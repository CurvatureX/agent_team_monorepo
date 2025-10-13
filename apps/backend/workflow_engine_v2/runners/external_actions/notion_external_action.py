"""
Notion External Action Implementation with AI-powered multi-round execution.

This module handles Notion operations through:
1. AI Loop Mode: Multi-round intelligent execution based on natural language instructions
2. Legacy Mode: Direct single-action execution with explicit action_type

Maximum 5 rounds enforced for AI loop mode with comprehensive telemetry.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from shared.models.execution_new import ExecutionStatus, NodeExecutionResult
from shared.sdks.notion_sdk.client import NotionClient
from shared.sdks.notion_sdk.exceptions import NotionAPIError
from workflow_engine_v2.core.context import NodeExecutionContext

from .base_external_action import BaseExternalAction
from .notion_ai_helpers import accumulate_context as helper_accumulate_context
from .notion_ai_helpers import build_ai_context as helper_build_ai_context
from .notion_ai_helpers import call_ai_model_anthropic, call_ai_model_openai


@dataclass
class RoundTelemetry:
    """Structured telemetry for each execution round."""

    round_num: int
    phase: str  # "planning" | "execution"

    # AI Decision
    decision_text: str  # Raw AI JSON output
    decision_parsed: Dict[str, Any]  # Parsed decision

    # Notion API Call
    api_call: Optional[Dict[str, Any]] = None  # {action_type, parameters}
    api_result: Optional[Dict[str, Any]] = None  # Response or error
    api_success: bool = True

    # Timing
    timestamp: str = ""
    duration_ms: int = 0

    # Context snapshot
    context_used: List[str] = field(default_factory=list)
    discovered_resources: Dict[str, Any] = field(default_factory=dict)


class NotionExternalAction(BaseExternalAction):
    """AI-powered Notion external action with strict 5-round limit."""

    MAX_ROUNDS = 5
    MAX_PLAN_STEPS = 4  # Round 1 for planning, rounds 2-5 for execution

    def __init__(self):
        super().__init__(integration_name="notion")
        self._anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self._openai_api_key = os.getenv("OPENAI_API_KEY")

    def _create_success_result(
        self,
        notion_response: Dict[str, Any],
        resource_id: str = "",
        resource_url: str = "",
        execution_metadata: Dict[str, Any] = None,
    ) -> NodeExecutionResult:
        """Create a success result matching the Notion spec output_params."""
        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data={
                "success": True,
                "notion_response": notion_response,
                "resource_id": resource_id,
                "resource_url": resource_url,
                "error_message": "",
                "rate_limit_info": {},
                "execution_metadata": execution_metadata or {},
            },
        )

    async def handle_operation(
        self, context: NodeExecutionContext, operation: str
    ) -> NodeExecutionResult:
        """Execute AI-powered multi-round Notion operations."""
        instruction = context.input_data.get("instruction", "").strip()

        if not instruction:
            return self.create_error_result(
                "Missing required 'instruction' parameter",
                "ai_execution",
                {
                    "error": "instruction parameter is required for Notion External Action",
                    "solution": "Provide a natural language instruction describing what to do in Notion",
                },
            )

        # Validate configuration based on operation_type
        configuration = context.node.configurations or {}
        operation_type = configuration.get("operation_type", "database")

        # Extract IDs directly from configuration (simplified structure)
        page_id = configuration.get("page_id", "").strip()
        database_id = configuration.get("database_id", "").strip()

        if operation_type == "page" and not page_id:
            self.log_execution(
                context,
                "⚠️ operation_type is 'page' but page_id not configured. AI will need to discover the page.",
                "WARNING",
            )
        elif operation_type == "database" and not database_id:
            self.log_execution(
                context,
                "⚠️ operation_type is 'database' but database_id not configured. AI will need to discover the database.",
                "WARNING",
            )
        elif operation_type == "both":
            # For 'both', at least one ID should be configured
            if not page_id and not database_id:
                self.log_execution(
                    context,
                    "⚠️ operation_type is 'both' but neither page_id nor database_id configured. AI will need to discover resources.",
                    "WARNING",
                )
            elif not page_id:
                self.log_execution(
                    context,
                    "ℹ️ operation_type is 'both' but only database_id configured. Page operations will require discovery.",
                    "INFO",
                )
            elif not database_id:
                self.log_execution(
                    context,
                    "ℹ️ operation_type is 'both' but only page_id configured. Database operations will require discovery.",
                    "INFO",
                )

        # AI-powered multi-round execution
        self.log_execution(
            context,
            f"🤖 AI Mode [{operation_type}]: {instruction[:100]}...",
        )
        return await self._execute_ai_loop(context, instruction)

    async def _execute_ai_loop(
        self, context: NodeExecutionContext, instruction: str
    ) -> NodeExecutionResult:
        """Multi-round AI execution with HARD 5-round limit."""
        start_time = datetime.utcnow()

        # Initialize execution state
        execution_state = {
            "instruction": instruction,
            "user_context": context.input_data.get("context", {}),
            "plan": None,
            "current_step": 0,
            "rounds": [],
            "discovered_resources": {},
            "schemas_cache": {},  # Cache database schemas
            "completed": False,
            "failures": [],
        }

        # Get Notion OAuth token once
        notion_token = await self.get_oauth_token(context)
        if not notion_token:
            return self.create_error_result(
                "No Notion OAuth token found", "ai_execution", {"instruction": instruction}
            )

        # Build comprehensive context (5 layers)
        ai_context = await self._build_ai_context(context, instruction, execution_state)

        async with NotionClient(auth_token=notion_token) as client:
            for round_num in range(1, self.MAX_ROUNDS + 1):
                round_start = datetime.utcnow()

                self.log_execution(
                    context,
                    f"🔄 Round {round_num}/{self.MAX_ROUNDS}: {'Planning' if round_num == 1 else 'Execution'}",
                )

                # AI Decision Phase
                try:
                    ai_decision = await self._get_ai_decision(
                        round_num=round_num,
                        rounds_remaining=self.MAX_ROUNDS - round_num,
                        instruction=instruction,
                        execution_state=execution_state,
                        ai_context=ai_context,
                        context=context,
                    )
                except Exception as e:
                    self.log_execution(context, f"❌ AI decision failed: {str(e)}", "ERROR")
                    break

                # Initialize round telemetry
                round_telemetry = RoundTelemetry(
                    round_num=round_num,
                    phase=(
                        "planning"
                        if round_num == 1 and ai_decision.get("planning_phase")
                        else "execution"
                    ),
                    decision_text=json.dumps(ai_decision, indent=2),
                    decision_parsed=ai_decision,
                    timestamp=datetime.utcnow().isoformat(),
                    context_used=ai_decision.get("context_used", []),
                )

                # Round 1: Store the plan (if provided)
                if round_num == 1 and "plan" in ai_decision:
                    plan = ai_decision.get("plan", [])
                    if len(plan) > self.MAX_PLAN_STEPS:
                        return self.create_error_result(
                            f"Plan has {len(plan)} steps, exceeds maximum {self.MAX_PLAN_STEPS}",
                            "ai_execution",
                            {
                                "instruction": instruction,
                                "plan_steps": len(plan),
                                "max_allowed": self.MAX_PLAN_STEPS,
                            },
                        )
                    execution_state["plan"] = plan
                    self.log_execution(context, f"📋 Plan created: {len(plan)} steps")

                # Notion Execution Phase
                action_type = ai_decision.get("action_type")
                parameters = ai_decision.get("parameters", {})

                # Handle sentinel values that signal "no operation needed"
                SENTINEL_ACTIONS = ["complete", "none", "skip", "finish", "done"]

                if not action_type or action_type.lower() in SENTINEL_ACTIONS:
                    if action_type and action_type.lower() in SENTINEL_ACTIONS:
                        self.log_execution(
                            context,
                            f"⏭️ AI signaled '{action_type}' - skipping Notion API execution",
                        )
                    else:
                        self.log_execution(context, "⚠️ AI decision missing action_type", "WARNING")

                    # Update telemetry without API call
                    round_telemetry.api_call = None
                    round_telemetry.api_success = True
                    round_telemetry.discovered_resources = execution_state[
                        "discovered_resources"
                    ].copy()
                    round_telemetry.duration_ms = int(
                        (datetime.utcnow() - round_start).total_seconds() * 1000
                    )
                    execution_state["rounds"].append(asdict(round_telemetry))

                    # Check if task is marked as completed
                    if ai_decision.get("completed", False):
                        execution_state["completed"] = True
                        self.log_execution(context, "✅ AI marked task as completed")
                        break

                    continue

                # Log API call
                round_telemetry.api_call = {"action_type": action_type, "parameters": parameters}

                try:
                    action_result = await self._execute_notion_action(
                        client=client,
                        action_type=action_type,
                        parameters=parameters,
                        context=context,
                    )

                    round_telemetry.api_success = True
                    round_telemetry.api_result = action_result

                    self.log_execution(context, f"✅ {action_type} executed successfully")

                except Exception as e:
                    round_telemetry.api_success = False
                    round_telemetry.api_result = {"error": str(e)}

                    self.log_execution(context, f"❌ {action_type} failed: {str(e)}", "ERROR")
                    execution_state["failures"].append(
                        {
                            "round": round_num,
                            "action_type": action_type,
                            "error": str(e),
                        }
                    )
                    # Continue to next round despite error

                # Accumulate discovered resources
                if round_telemetry.api_success:
                    self._accumulate_context(
                        execution_state=execution_state,
                        action_type=action_type,
                        result=action_result,
                    )

                # Update telemetry
                round_telemetry.discovered_resources = execution_state[
                    "discovered_resources"
                ].copy()
                round_telemetry.duration_ms = int(
                    (datetime.utcnow() - round_start).total_seconds() * 1000
                )

                # Store round telemetry
                execution_state["rounds"].append(asdict(round_telemetry))

                # Check if AI says we're done (after executing the action)
                if ai_decision.get("completed", False):
                    execution_state["completed"] = True
                    if round_telemetry.api_success:
                        self.log_execution(context, "✅ AI marked task as completed")
                    else:
                        self.log_execution(
                            context,
                            "⚠️ AI marked task completed but the last action failed",
                            "WARNING",
                        )
                    break

                # Update context for next round
                ai_context["execution_history"] = execution_state["rounds"]
                ai_context["notion_context"] = execution_state["discovered_resources"]
                ai_context["schemas_cache"] = execution_state["schemas_cache"]

        # Build final result
        total_duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        if not execution_state["completed"]:
            self.log_execution(
                context,
                f"⚠️ Reached maximum {self.MAX_ROUNDS} rounds without completion",
                "WARNING",
            )

        # Return result matching node spec output_params
        operation_success = execution_state["completed"] and not execution_state["failures"]

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            output_data={
                "success": operation_success,
                "resource_id": "",  # No single resource for multi-round execution
                "resource_url": "",
                "error_message": "",
                "ai_execution": {
                    "plan": execution_state["plan"],
                    "rounds_executed": len(execution_state["rounds"]),
                    "max_rounds": self.MAX_ROUNDS,
                    "rounds": execution_state["rounds"],
                    "completed": execution_state["completed"],
                    "hit_round_limit": len(execution_state["rounds"]) == self.MAX_ROUNDS
                    and not execution_state["completed"],
                    "total_duration_ms": total_duration_ms,
                    "failures": execution_state["failures"],
                },
                "discovered_resources": execution_state["discovered_resources"],
            },
        )

    async def _build_ai_context(
        self, context: NodeExecutionContext, instruction: str, execution_state: dict
    ) -> dict:
        """Build comprehensive 5-layer context with operation_type awareness."""
        ai_context = await helper_build_ai_context(context, instruction, execution_state)

        # Add operation_type configuration to context (simplified)
        operation_type = context.node.configurations.get("operation_type", "database")
        page_id = context.node.configurations.get("page_id", "").strip()
        database_id = context.node.configurations.get("database_id", "").strip()

        ai_context["configuration"] = {
            "operation_type": operation_type,
            "page_id": page_id,
            "database_id": database_id,
        }

        # Include cached schemas so AI can see actual database properties
        ai_context["schemas_cache"] = execution_state["schemas_cache"]

        return ai_context

    async def _get_ai_decision(
        self,
        round_num: int,
        rounds_remaining: int,
        instruction: str,
        execution_state: dict,
        ai_context: dict,
        context: NodeExecutionContext,
    ) -> dict:
        """Generate AI decision with round budget awareness."""
        # Build comprehensive system prompt for Notion AI loop
        system_prompt = """You are an AI assistant that executes Notion operations through a multi-round execution system.

**YOUR TASK:** Break down natural language instructions into Notion API operations and execute them intelligently.

**CRITICAL OUTPUT FORMAT:**
Your response MUST be raw JSON only. Do NOT wrap it in markdown code blocks (```json), do NOT use backticks, do NOT add any explanatory text before or after the JSON.

Example of CORRECT output:
{"action_type": "search", "parameters": {"query": "test"}, "reasoning": "...", "completed": false, "planning_phase": false, "plan": []}

Example of INCORRECT output (DO NOT DO THIS):
```json
{"action_type": "search", ...}
```

**CRITICAL RULES:**
1. **Output ONLY raw JSON** - No markdown fences, no backticks, no explanations, no code blocks
2. **Maximum 5 rounds total** - Plan efficiently within budget
3. **MANDATORY: Use cached schemas** - If a database schema is cached, you MUST use the exact property names shown. NEVER guess or invent property names like "Name", "Description", "Assignee" - only use properties that exist in the cached schema
4. **Schema retrieval** - If schema not cached, retrieve database first before creating/updating pages
5. **Resource accumulation** - Use discovered resources from previous rounds
6. **Keep responses concise** - Limit content blocks to 3-5 items maximum per operation to avoid token limits
7. **Reuse configured resources** - If page_id or database_id is configured, use them directly. Do NOT create new pages/databases or search for them.

**Available Notion Operations:**
- search: Find databases/pages by query
- retrieve_database: Get database schema and properties
- retrieve_page: Get page properties (title, created_time, etc.)
- retrieve_block_children: Get all child blocks of a page/block (use this to see page content!)
- create_page: Create new page in database or as child of page
- update_page: Update existing page properties/content
- append_blocks: Add content blocks to page
- update_block: Modify existing block content (paragraph text, heading, etc.)
- delete_block: Remove/archive a single block
- batch_delete_blocks: Delete multiple blocks at once (efficient for bulk cleanup!)
- query_database: Query database with filters/sorts
- update_database: Update database properties and schema

**Batch Operations & Caching:**
- Use batch_delete_blocks to delete multiple blocks efficiently in one operation
- Pass an array of block_ids: {"block_ids": ["id1", "id2", "id3", ...]}
- **IMPORTANT**: After retrieving blocks with retrieve_block_children, the block IDs are cached in discovered_resources
- Check discovered_resources for cached block_ids before retrieving again
- Use cached block_ids directly for batch operations to save rounds

**Common Patterns:**

Pattern A: Append to Configured Page (page_id is configured)
- Round 1: append_blocks with page_id and children blocks
- Do NOT create a new page - the page already exists

Pattern B: Create Page in Configured Database (database_id is configured)
- Round 1: retrieve_database to get schema (check Cached Database Schemas first - may already be cached!)
- Round 2: create_page with parent: {"database_id": "..."} and properties using ONLY property names from cached schema

Pattern C: Update Existing Page (page_id is configured)
- Round 1: retrieve_block_children to get current content
- Round 2: batch_delete_blocks or append_blocks to modify content

**JSON Response Format:**
{
  "action_type": "operation_name",  // Use "complete" to skip execution when task is done
  "parameters": { /* operation-specific params */ },
  "reasoning": "Brief explanation of this step",
  "completed": false,  // true only when task is fully done
  "planning_phase": false,  // true only for Round 1 planning
  "plan": []  // only for Round 1: array of {step, action_type}
}

**Completion Signal:**
When the task is complete and no further Notion operations are needed:
- Set `completed: true`
- Set `action_type: "complete"` (or "done", "none") to skip API execution
- The system will exit the loop successfully

**FINAL REMINDER - OUTPUT FORMAT:**
Return ONLY raw JSON. No markdown code blocks (```json), no backticks, no explanations.
Your entire response should be parseable by JSON.parse() directly.
Start your response with { and end with }"""

        # Build user message with full context
        configuration = ai_context.get("configuration", {})
        operation_type = configuration.get("operation_type", "database")
        page_id = configuration.get("page_id", "")
        database_id = configuration.get("database_id", "")

        user_message = f"""**Round {round_num}/{self.MAX_ROUNDS}** (⏱️ {rounds_remaining} rounds remaining)

**Instruction:** {instruction}

**Node Configuration:**
- Operation Type: {operation_type}
- Page ID: {page_id if page_id else "(not configured)"}
- Database ID: {database_id if database_id else "(not configured)"}

**Configuration Guidance:**
- When page_id is configured: **REUSE the existing page** - Do NOT create a new page. Append blocks, update properties, or read content from this page.
- When database_id is configured: **REUSE the existing database** - Create new pages IN this database, or query/update it.
- When operation_type is "page": Use the configured page_id for all page operations
- When operation_type is "database": Use the configured database_id for database operations
- When operation_type is "both": You can use either page_id or database_id as needed
- **IMPORTANT**: If a resource ID is already configured, do NOT search for it or create a new one. Use the provided ID directly.
- **CRITICAL**: Check "Cached Database Schemas" section below - if a database schema is already cached, you MUST use those exact property names. Do NOT invent properties!

**Available Context:**

### User-Provided Context:
```json
{json.dumps(ai_context["user_context"], indent=2)}
```

### Workflow Context:
- Trigger: {ai_context["workflow_context"]["trigger_type"]}
- Trigger Data:
```json
{json.dumps(ai_context["workflow_context"]["trigger_data"], indent=2)}
```
- Workflow: {ai_context["workflow_context"]["workflow_name"]}

### Previous Node Outputs:
```json
{json.dumps(ai_context["previous_outputs"], indent=2)}
```

### Execution History:
{self._format_execution_history(ai_context["execution_history"])}

### Discovered Notion Resources:
```json
{json.dumps(ai_context["notion_context"], indent=2)}
```

### Cached Database Schemas:
{self._format_cached_schemas(ai_context.get("schemas_cache", {}))}

**Round Budget:**
- Current: {round_num}/{self.MAX_ROUNDS}
- Remaining: {rounds_remaining}
- If planning phase: Maximum {self.MAX_PLAN_STEPS} steps allowed

**Your Task:**
{self._get_round_specific_prompt(round_num, rounds_remaining, execution_state)}
"""

        # Call AI model (prefer Anthropic, fallback to OpenAI)
        if self._anthropic_api_key:
            return await call_ai_model_anthropic(
                api_key=self._anthropic_api_key,
                system_prompt=system_prompt,
                user_message=user_message,
            )
        elif self._openai_api_key:
            return await call_ai_model_openai(
                api_key=self._openai_api_key,
                system_prompt=system_prompt,
                user_message=user_message,
            )
        else:
            raise ValueError(
                "No AI API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable."
            )

    def _format_execution_history(self, rounds: List[dict]) -> str:
        """Format execution history for AI context."""
        if not rounds:
            return "(No previous rounds yet)"

        history_lines = []
        for r in rounds:
            round_num = r.get("round_num", "?")
            decision = r.get("decision_parsed", {})
            api_call = r.get("api_call")
            success = r.get("api_success", True)

            line = f"Round {round_num}: "
            if api_call:
                action = api_call.get("action_type", "unknown")
                status = "✅ Success" if success else "❌ Failed"
                line += f"{action} ({status})"
            else:
                line += "Planning/Completion"

            history_lines.append(line)

        return "\n".join(history_lines)

    def _format_cached_schemas(self, schemas_cache: Dict[str, Any]) -> str:
        """Format cached database schemas for AI context."""
        if not schemas_cache:
            return "(No database schemas cached yet - retrieve database first to see properties)"

        schema_lines = []
        for db_id, schema_data in schemas_cache.items():
            properties = schema_data.get("properties", [])
            schema_lines.append(f"**Database {db_id}:**")
            schema_lines.append(f"- Available properties: {', '.join(properties)}")
            schema_lines.append(
                f"- IMPORTANT: Use these exact property names when creating/updating pages"
            )
            schema_lines.append("")

        return "\n".join(schema_lines)

    def _get_round_specific_prompt(
        self, round_num: int, rounds_remaining: int, execution_state: dict
    ) -> str:
        """Generate round-specific guidance."""
        if round_num == 1:
            return f"""
Analyze the instruction and context. Choose strategy:
- **Simple task (1-2 operations)**: Execute directly using Pattern 2, no planning phase needed
- **Complex task (3-4 operations)**: Create plan with ≤{self.MAX_PLAN_STEPS} steps using Pattern 1

If task requires >4 steps, return error explaining it exceeds budget.
"""
        elif rounds_remaining == 0:
            return """
**FINAL ROUND** - This is your last chance!
- Complete the most critical operation
- OR mark task as completed if already satisfied
- OR return graceful failure if impossible to complete
"""
        else:
            return f"""
Execute the next planned step or direct action.
Remaining budget: {rounds_remaining} rounds.
Be efficient - prefer completing in fewer rounds.
"""

    def _accumulate_context(self, execution_state: dict, action_type: str, result: dict) -> None:
        """Extract and cache discovered resources."""
        helper_accumulate_context(execution_state, action_type, result)

    async def _execute_notion_action(
        self,
        client: NotionClient,
        action_type: str,
        parameters: dict,
        context: NodeExecutionContext,
    ) -> dict:
        """Execute a single Notion action based on AI decision."""
        action_type_normalized = action_type.lower().replace("-", "_")

        # Route to appropriate SDK method
        if action_type_normalized == "search":
            query = parameters.get("query", "")
            filter_obj = parameters.get("filter", {})
            page_size = parameters.get("page_size", 10)

            # Build filter_conditions for Notion API
            filter_conditions = None
            if filter_obj:
                if isinstance(filter_obj, dict):
                    # If it has 'property' and 'value', use as-is (proper Notion API format)
                    if "property" in filter_obj and "value" in filter_obj:
                        filter_conditions = filter_obj
                    # If it just has 'value', assume it's an object type filter
                    elif "value" in filter_obj:
                        filter_conditions = {"property": "object", "value": filter_obj["value"]}
                    else:
                        # Use the dict as-is, might be a complete filter
                        filter_conditions = filter_obj
                elif isinstance(filter_obj, str):
                    # String filter, assume it's an object type
                    filter_conditions = {"property": "object", "value": filter_obj}

            result = await client.search(
                query=query, filter_conditions=filter_conditions, page_size=page_size
            )

            return {
                "notion_response": {
                    "object": "list",
                    "results": [asdict(item) for item in result["results"]],
                    "has_more": result.get("has_more", False),
                    "next_cursor": result.get("next_cursor"),
                },
                "resource_id": "",
                "execution_metadata": {
                    "action_type": "search",
                    "query": query,
                    "result_count": len(result["results"]),
                },
            }

        elif action_type_normalized == "retrieve_database":
            database_id = parameters.get("database_id", "").replace("-", "")
            database = await client.get_database(database_id)

            return {
                "notion_response": asdict(database),
                "resource_id": database.id,
                "execution_metadata": {"action_type": "retrieve_database"},
            }

        elif action_type_normalized == "retrieve_page":
            page_id = parameters.get("page_id", "").replace("-", "")
            page = await client.get_page(page_id)

            return {
                "notion_response": asdict(page),
                "resource_id": page.id,
                "resource_url": page.url,
                "execution_metadata": {"action_type": "retrieve_page"},
            }

        elif action_type_normalized == "create_page":
            parent = parameters.get("parent", {})
            properties = parameters.get("properties", {})
            children = parameters.get("children", [])

            resolved_parent = self._ensure_parent(parent, context)
            parameters["parent"] = resolved_parent

            page = await client.create_page(
                parent=resolved_parent, properties=properties, children=children
            )

            return {
                "notion_response": asdict(page),
                "resource_id": page.id,
                "resource_url": page.url,
                "execution_metadata": {"action_type": "create_page"},
            }

        elif action_type_normalized == "update_page":
            page_id = parameters.get("page_id", "").replace("-", "")
            properties = parameters.get("properties", {})

            page = await client.update_page(page_id, properties)

            return {
                "notion_response": asdict(page),
                "resource_id": page.id,
                "resource_url": page.url,
                "execution_metadata": {"action_type": "update_page"},
            }

        elif action_type_normalized == "update_database":
            database_id = parameters.get("database_id", "").replace("-", "")
            properties = parameters.get("properties", {})

            database = await client.update_database(database_id, properties=properties)

            return {
                "notion_response": asdict(database),
                "resource_id": database.id,
                "execution_metadata": {"action_type": "update_database"},
            }

        elif action_type_normalized == "append_blocks":
            # Accept either block_id or page_id (Notion API uses block_id)
            block_id = parameters.get("block_id") or parameters.get("page_id", "")
            block_id = block_id.replace("-", "")
            children = parameters.get("children", [])

            result = await client.append_block_children(block_id=block_id, children=children)

            return {
                "notion_response": {
                    "object": "list",
                    "results": [asdict(block) for block in result["blocks"]],
                },
                "resource_id": block_id,
                "execution_metadata": {"action_type": "append_blocks", "block_id": block_id},
            }

        elif action_type_normalized == "retrieve_block_children":
            block_id = parameters.get("block_id") or parameters.get("page_id", "")
            block_id = block_id.replace("-", "")
            page_size = parameters.get("page_size", 100)

            result = await client.get_block_children(block_id=block_id, page_size=page_size)

            return {
                "notion_response": {
                    "object": "list",
                    "results": [asdict(block) for block in result["blocks"]],
                    "has_more": result.get("has_more", False),
                    "next_cursor": result.get("next_cursor"),
                },
                "resource_id": block_id,
                "execution_metadata": {
                    "action_type": "retrieve_block_children",
                    "block_id": block_id,
                    "block_count": len(result["blocks"]),
                },
            }

        elif action_type_normalized == "update_block":
            block_id = parameters.get("block_id", "").replace("-", "")
            block_data = parameters.get("block_data", {})
            archived = parameters.get("archived")

            result = await client.update_block(
                block_id=block_id, block_data=block_data, archived=archived
            )

            return {
                "notion_response": asdict(result),
                "resource_id": block_id,
                "execution_metadata": {
                    "action_type": "update_block",
                    "block_id": block_id,
                },
            }

        elif action_type_normalized == "delete_block":
            block_id = parameters.get("block_id", "").replace("-", "")

            result = await client.delete_block(block_id=block_id)

            return {
                "notion_response": asdict(result),
                "resource_id": block_id,
                "execution_metadata": {
                    "action_type": "delete_block",
                    "block_id": block_id,
                },
            }

        elif action_type_normalized == "batch_delete_blocks":
            block_ids = parameters.get("block_ids", [])

            if not block_ids:
                raise ValueError("batch_delete_blocks requires a list of block_ids")

            # Delete blocks in parallel for performance
            deleted_blocks = []
            failed_blocks = []

            for block_id in block_ids:
                try:
                    block_id_clean = block_id.replace("-", "")
                    result = await client.delete_block(block_id=block_id_clean)
                    deleted_blocks.append(
                        {
                            "id": block_id_clean,
                            "status": "deleted",
                            "archived": result.archived,
                        }
                    )
                except Exception as e:
                    failed_blocks.append(
                        {
                            "id": block_id,
                            "status": "failed",
                            "error": str(e),
                        }
                    )

            return {
                "notion_response": {
                    "deleted": deleted_blocks,
                    "failed": failed_blocks,
                    "total_requested": len(block_ids),
                    "total_deleted": len(deleted_blocks),
                    "total_failed": len(failed_blocks),
                },
                "resource_id": "",
                "execution_metadata": {
                    "action_type": "batch_delete_blocks",
                    "total_requested": len(block_ids),
                    "total_deleted": len(deleted_blocks),
                    "total_failed": len(failed_blocks),
                },
            }

        elif action_type_normalized == "query_database":
            database_id = parameters.get("database_id", "").replace("-", "")
            filter_conditions = parameters.get("filter")
            sorts = parameters.get("sorts", [])
            page_size = parameters.get("page_size", 100)

            result = await client.query_database(
                database_id, filter_conditions=filter_conditions, sorts=sorts, page_size=page_size
            )

            return {
                "notion_response": result,
                "results": result["pages"],
                "execution_metadata": {
                    "action_type": "query_database",
                    "database_id": database_id,
                },
            }

        else:
            raise ValueError(f"Unsupported Notion action_type: {action_type}")

    def _ensure_parent(
        self, parent: Dict[str, Any], context: NodeExecutionContext
    ) -> Dict[str, Any]:
        """Ensure parent payload contains database_id/page_id derived from workflow configuration."""

        parent = parent or {}
        # If parent already has valid IDs, return it
        if parent.get("database_id") or parent.get("page_id") or parent.get("workspace"):
            return parent

        # Otherwise, use IDs from node configuration
        config = context.node.configurations or {}

        def _sanitize(notion_id: Optional[str]) -> Optional[str]:
            if not notion_id or not isinstance(notion_id, str):
                return None
            return notion_id.replace("-", "").strip()

        database_id = _sanitize(config.get("database_id"))
        page_id = _sanitize(config.get("page_id"))

        # Prefer database_id if configured
        if database_id:
            return {"database_id": database_id}
        # Fall back to page_id
        if page_id:
            return {"page_id": page_id}

        # No configuration available; return empty parent so error surfaces
        return parent

    async def _search(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Search Notion workspace."""
        query = context.input_data.get("query", "")
        filter_obj = context.input_data.get("filter", {})
        page_size = context.input_data.get("page_size", 10)

        # Build filter_conditions for Notion API
        filter_conditions = None
        if filter_obj:
            filter_type = filter_obj.get("value", "page")
            filter_conditions = {"property": "object", "value": filter_type}

        self.log_execution(
            context, f"Searching Notion: query='{query}', filter={filter_conditions}"
        )

        result = await client.search(
            query=query, filter_conditions=filter_conditions, page_size=page_size
        )

        self.log_execution(context, f"✅ Found {len(result['results'])} items")

        return self._create_success_result(
            notion_response={
                "object": "list",
                "results": [asdict(item) for item in result["results"]],
                "has_more": result.get("has_more", False),
                "next_cursor": result.get("next_cursor"),
            },
            resource_id="",
            resource_url="",
            execution_metadata={
                "action_type": "search",
                "query": query,
                "result_count": len(result["results"]),
            },
        )

    async def _get_page(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Get a Notion page."""
        page_id = context.input_data.get("page_id", "").replace("-", "")

        if not page_id:
            return self.create_error_result("page_id is required", "get_page")

        page = await client.get_page(page_id)

        return self._create_success_result(
            notion_response=asdict(page),
            resource_id=page.id,
            resource_url=page.url,
            execution_metadata={"action_type": "get_page", "page_id": page_id},
        )

    async def _create_page(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Create a Notion page."""
        parent = context.input_data.get("parent", {})
        properties = context.input_data.get("properties", {})
        children = context.input_data.get("children", [])

        if not parent:
            return self.create_error_result("parent is required", "create_page")

        page = await client.create_page(parent=parent, properties=properties, children=children)

        self.log_execution(context, f"✅ Created page: {page.id}")

        return self._create_success_result(
            notion_response=asdict(page),
            resource_id=page.id,
            resource_url=page.url,
            execution_metadata={"action_type": "create_page", "parent": parent},
        )

    async def _update_page(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Update a Notion page."""
        page_id = context.input_data.get("page_id", "").replace("-", "")
        properties = context.input_data.get("properties", {})

        if not page_id:
            return self.create_error_result("page_id is required", "update_page")

        page = await client.update_page(page_id, properties)

        self.log_execution(context, f"✅ Updated page: {page_id}")

        return self._create_success_result(
            notion_response=asdict(page),
            resource_id=page.id,
            resource_url=page.url,
            execution_metadata={"action_type": "update_page", "page_id": page_id},
        )

    async def _get_database(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Get a Notion database."""
        database_id = context.input_data.get("database_id", "").replace("-", "")

        if not database_id:
            return self.create_error_result("database_id is required", "get_database")

        database = await client.get_database(database_id)

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "database": asdict(database),
                "resource_id": database.id,
            },
        )

    async def _query_database(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Query a Notion database."""
        database_id = context.input_data.get("database_id", "").replace("-", "")
        filter_conditions = context.input_data.get("filter")
        sorts = context.input_data.get("sorts", [])
        page_size = context.input_data.get("page_size", 100)

        if not database_id:
            return self.create_error_result("database_id is required", "query_database")

        result = await client.query_database(
            database_id, filter_conditions=filter_conditions, sorts=sorts, page_size=page_size
        )

        self.log_execution(context, f"✅ Queried database: {len(result['results'])} results")

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "results": result["results"],
                "has_more": result.get("has_more", False),
                "next_cursor": result.get("next_cursor"),
            },
        )

    async def _create_database(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Create a Notion database."""
        parent = context.input_data.get("parent", {})
        title = context.input_data.get("title", [])
        properties = context.input_data.get("properties", {})

        if not parent:
            return self.create_error_result("parent is required", "create_database")

        database = await client.create_database(parent=parent, title=title, properties=properties)

        self.log_execution(context, f"✅ Created database: {database.id}")

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "database": asdict(database),
                "resource_id": database.id,
            },
        )

    async def _update_database(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Update a Notion database."""
        database_id = context.input_data.get("database_id", "").replace("-", "")
        title = context.input_data.get("title")
        properties = context.input_data.get("properties")

        if not database_id:
            return self.create_error_result("database_id is required", "update_database")

        database = await client.update_database(database_id, title=title, properties=properties)

        self.log_execution(context, f"✅ Updated database: {database_id}")

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "database": asdict(database),
                "resource_id": database.id,
            },
        )

    async def _get_block(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Get a Notion block."""
        block_id = context.input_data.get("block_id", "").replace("-", "")

        if not block_id:
            return self.create_error_result("block_id is required", "get_block")

        block = await client.get_block(block_id)

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "block": asdict(block),
                "resource_id": block.id,
            },
        )

    async def _get_block_children(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Get children of a Notion block."""
        # Handle both direct input and conversion-function-wrapped input
        block_id = (
            context.input_data.get("block_id")
            or context.input_data.get("data", {}).get("block_id")
            or context.input_data.get("result", {}).get("data", {}).get("block_id")
            or ""
        )
        if block_id:
            block_id = block_id.replace("-", "")

        page_size = (
            context.input_data.get("page_size")
            or context.input_data.get("data", {}).get("page_size")
            or context.input_data.get("result", {}).get("data", {}).get("page_size")
            or 100
        )

        if not block_id:
            return self.create_error_result("block_id is required", "get_block_children")

        result = await client.get_block_children(block_id, page_size=page_size)

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "blocks": [asdict(block) for block in result["blocks"]],
                "has_more": result.get("has_more", False),
                "next_cursor": result.get("next_cursor"),
            },
        )

    async def _append_blocks(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Append blocks to a Notion page or block."""
        # Get page_id or block_id and children from input
        # Handle both direct input and conversion-function-wrapped input (result.data)
        page_id = (
            context.input_data.get("page_id")
            or context.input_data.get("data", {}).get("page_id")
            or context.input_data.get("result", {})
            .get("data", {})
            .get("page_id")  # From conversion function
            or context.node.configurations.get("page_id", "")  # Simplified: directly from config
        )

        children = (
            context.input_data.get("children")
            or context.input_data.get("data", {}).get("children")
            or context.input_data.get("result", {})
            .get("data", {})
            .get("children")  # From conversion function
            or []  # No default children from config
        )

        if not page_id:
            return self.create_error_result(
                "page_id is required for append_blocks", "append_blocks"
            )

        if not children:
            return self.create_error_result(
                "children blocks array is required for append_blocks", "append_blocks"
            )

        # Remove hyphens from page_id
        page_id = page_id.replace("-", "")

        self.log_execution(context, f"Appending {len(children)} block(s) to page {page_id[:8]}...")

        result = await client.append_block_children(block_id=page_id, children=children)

        self.log_execution(context, f"✅ Appended {len(children)} block(s) to page")

        return self._create_success_result(
            notion_response={
                "object": "list",
                "results": [asdict(block) for block in result["blocks"]],
                "next_cursor": result.get("next_cursor"),
                "has_more": result.get("has_more", False),
            },
            resource_id=page_id,
            resource_url=f"https://www.notion.so/{page_id}",
            execution_metadata={
                "action_type": "append_blocks",
                "page_id": page_id,
                "blocks_appended": len(children),
            },
        )

    async def _update_block(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Update a Notion block."""
        block_id = context.input_data.get("block_id", "").replace("-", "")
        block_data = context.input_data.get("block_data", {})

        if not block_id:
            return self.create_error_result("block_id is required", "update_block")

        block = await client.update_block(block_id, block_data)

        self.log_execution(context, f"✅ Updated block: {block_id}")

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "block": asdict(block),
                "resource_id": block.id,
            },
        )

    async def _delete_block(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Delete (archive) a Notion block."""
        block_id = context.input_data.get("block_id", "").replace("-", "")

        if not block_id:
            return self.create_error_result("block_id is required", "delete_block")

        block = await client.delete_block(block_id)

        self.log_execution(context, f"✅ Deleted block: {block_id}")

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "block": asdict(block),
                "resource_id": block.id,
            },
        )

    async def _list_users(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """List Notion workspace users."""
        page_size = context.input_data.get("page_size", 100)

        result = await client.list_users(page_size=page_size)

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "users": [asdict(user) for user in result["users"]],
                "has_more": result.get("has_more", False),
                "next_cursor": result.get("next_cursor"),
            },
        )

    async def _get_user(
        self, context: NodeExecutionContext, client: NotionClient
    ) -> NodeExecutionResult:
        """Get a Notion user."""
        user_id = context.input_data.get("user_id", "")

        if not user_id:
            return self.create_error_result("user_id is required", "get_user")

        user = await client.get_user(user_id)

        return NodeExecutionResult(
            status=ExecutionStatus.SUCCESS,
            outputs={
                "success": True,
                "user": asdict(user),
                "resource_id": user.id,
            },
        )
