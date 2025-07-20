"""
Intelligent Design Engine for Workflow Agent
Complete implementation of IntelligentDesigner and WorkflowOrchestrator
Based on MVP plan and architecture design
"""

import json
from datetime import datetime
from typing import Any, Dict, List

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from core.config import settings
from core.vector_store import get_node_knowledge_rag

logger = structlog.get_logger()


class IntelligentDesigner:
    """
    Complete intelligent design engine as per MVP plan
    Handles architecture design and DSL generation
    """

    def __init__(self):
        self.llm = self._setup_llm()
        self.pattern_library = self._load_pattern_library()
        self.optimization_rules = self._load_optimization_rules()
        self.performance_models = self._load_performance_models()
        self.rag = get_node_knowledge_rag()

    def _setup_llm(self):
        """Setup the language model based on configuration"""
        if settings.DEFAULT_MODEL_PROVIDER == "openai":
            return ChatOpenAI(
                model_name=settings.DEFAULT_MODEL_NAME,
                openai_api_key=settings.OPENAI_API_KEY,
                temperature=0.1,
            )
        elif settings.DEFAULT_MODEL_PROVIDER == "anthropic":
            return ChatAnthropic(
                model_name=settings.DEFAULT_MODEL_NAME,
                anthropic_api_key=settings.ANTHROPIC_API_KEY,
                temperature=0.1,
            )
        else:
            raise ValueError(f"Unsupported model provider: {settings.DEFAULT_MODEL_PROVIDER}")

    def _load_pattern_library(self) -> Dict[str, Any]:
        """Load architecture pattern library"""
        return {
            "customer_service_automation": {
                "pattern": "Trigger → AI_Analyzer → Conditional_Router → [AI_Response | Human_Escalation]",
                "nodes": [
                    {"type": "TRIGGER_EMAIL", "role": "trigger"},
                    {"type": "AI_TASK_ANALYZER", "role": "analysis"},
                    {"type": "FLOW_IF", "role": "routing"},
                    {"type": "AI_AGENT_NODE", "role": "response"},
                    {"type": "EXTERNAL_EMAIL", "role": "escalation"},
                ],
                "optimization": "并行AI分析+人工审核机制",
                "performance_estimate": {
                    "avg_response_time": "2-5秒",
                    "throughput": "100-500邮件/小时",
                    "reliability": "95%+ (含fallback)",
                },
            },
            "data_integration_pipeline": {
                "pattern": "Scheduler → Data_Extractor → AI_Transformer → Multi_Output",
                "nodes": [
                    {"type": "TRIGGER_CRON", "role": "trigger"},
                    {"type": "EXTERNAL_API", "role": "extraction"},
                    {"type": "AI_DATA_INTEGRATOR", "role": "transformation"},
                    {"type": "FLOW_PARALLEL", "role": "distribution"},
                    {"type": "EXTERNAL_NOTION", "role": "output"},
                    {"type": "EXTERNAL_SLACK", "role": "notification"},
                ],
                "optimization": "批处理+增量更新+错误重试",
                "performance_estimate": {
                    "processing_time": "5-30分钟/批次",
                    "data_quality": "90%+ (含验证)",
                },
            },
            "content_monitoring": {
                "pattern": "Multi_Trigger → Content_Aggregator → AI_Filter → Smart_Router → Action_Handler",
                "nodes": [
                    {"type": "TRIGGER_WEBHOOK", "role": "trigger"},
                    {"type": "AI_DATA_INTEGRATOR", "role": "aggregation"},
                    {"type": "AI_TASK_ANALYZER", "role": "filtering"},
                    {"type": "FLOW_IF", "role": "routing"},
                    {"type": "MEMORY_VECTOR_STORE", "role": "storage"},
                    {"type": "EXTERNAL_SLACK", "role": "notification"},
                ],
                "optimization": "智能去重+相关性分析+优先级排序",
                "performance_estimate": {
                    "processing_time": "实时处理",
                    "accuracy": "85%+ 相关性匹配",
                },
            },
            "automated_reporting": {
                "pattern": "Data_Collection → AI_Analysis → Report_Generation → Multi_Channel_Distribution",
                "nodes": [
                    {"type": "TRIGGER_CRON", "role": "trigger"},
                    {"type": "EXTERNAL_API", "role": "data_collection"},
                    {"type": "AI_DATA_INTEGRATOR", "role": "analysis"},
                    {"type": "AI_REPORT_GENERATOR", "role": "generation"},
                    {"type": "TRANSFORM_DATA", "role": "formatting"},
                    {"type": "FLOW_PARALLEL", "role": "distribution"},
                ],
                "optimization": "模板化生成+个性化内容+智能分发",
                "performance_estimate": {
                    "generation_time": "5-15分钟",
                    "quality_score": "90%+ 内容质量",
                },
            },
        }

    def _load_optimization_rules(self) -> Dict[str, Any]:
        """Load optimization rules"""
        return {
            "performance": {
                "parallel_processing": "识别可并行执行的节点",
                "caching": "添加缓存机制减少重复计算",
                "batch_processing": "批量处理提高效率",
                "lazy_loading": "延迟加载非关键数据",
            },
            "reliability": {
                "error_handling": "添加错误处理和重试机制",
                "fallback": "设计降级方案",
                "monitoring": "添加健康检查和监控",
                "validation": "数据验证和完整性检查",
            },
            "maintainability": {
                "modularity": "模块化设计便于维护",
                "configuration": "配置外部化",
                "documentation": "添加文档和注释",
                "testing": "可测试性设计",
            },
        }

    def _load_performance_models(self) -> Dict[str, Any]:
        """Load performance estimation models"""
        return {
            "node_costs": {
                "TRIGGER_EMAIL": {"cpu": 0.1, "memory": 0.05, "time": 1},
                "AI_TASK_ANALYZER": {"cpu": 2.0, "memory": 0.5, "time": 3},
                "EXTERNAL_API": {"cpu": 0.2, "memory": 0.1, "time": 2},
                "FLOW_IF": {"cpu": 0.05, "memory": 0.02, "time": 0.1},
                "MEMORY_VECTOR_STORE": {"cpu": 0.5, "memory": 1.0, "time": 1},
            },
            "scaling_factors": {
                "data_volume": {"small": 1.0, "medium": 2.0, "large": 5.0},
                "complexity": {"low": 1.0, "medium": 1.5, "high": 3.0},
                "concurrency": {"single": 1.0, "moderate": 1.2, "high": 2.0},
            },
        }

    async def decompose_to_task_tree(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decompose requirements into hierarchical task tree
        """
        logger.info("Starting task decomposition", requirements=requirements)

        # Extract main goals and constraints
        primary_goal = requirements.get("primary_goal", "")
        secondary_goals = requirements.get("secondary_goals", [])
        constraints = requirements.get("constraints", [])

        # Generate task decomposition using LLM
        system_prompt = """
        你是一个专业的工作流架构师。请将用户需求分解为层次化的任务树。

        任务分解原则：
        1. 识别主要任务和子任务
        2. 分析任务依赖关系
        3. 发现并行执行机会
        4. 考虑错误处理和边界情况

        重要：必须返回有效的JSON格式，不要添加任何解释文字。只返回JSON对象。

        返回JSON格式：
        {
          "root_task": "主要任务描述",
          "subtasks": [
            {
              "id": "task_id",
              "name": "任务名称",
              "description": "详细描述",
              "type": "sequential|parallel|conditional",
              "dependencies": ["dependency_task_ids"],
              "estimated_complexity": 1-10,
              "critical_path": true/false
            }
          ],
          "dependencies": [
            {"from": "task_a", "to": "task_b", "type": "sequential|data|conditional"}
          ],
          "parallel_opportunities": [["task1", "task2"], ["task3", "task4"]]
        }
        """

        user_prompt = f"""
        请分解以下需求：

        主要目标：{primary_goal}
        次要目标：{', '.join(secondary_goals)}
        约束条件：{', '.join(constraints)}

        请提供详细的任务分解。
        """

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        try:
            response = await self.llm.ainvoke(messages)
            response_content = response.content.strip()

            # Handle potential JSON parsing issues
            if not response_content:
                logger.warning("Empty response from LLM, using fallback")
                return self._create_fallback_task_tree(requirements)

            # Try to extract JSON from response if it's wrapped in markdown
            if response_content.startswith("```json"):
                response_content = response_content.split("```json")[1].split("```")[0].strip()
            elif response_content.startswith("```"):
                response_content = response_content.split("```")[1].split("```")[0].strip()

            task_tree = json.loads(response_content)

            # Validate and enhance task tree
            task_tree = self._validate_task_tree(task_tree)
            task_tree = self._enhance_task_tree(task_tree, requirements)

            logger.info(
                "Task decomposition completed", task_count=len(task_tree.get("subtasks", []))
            )
            return task_tree

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                "JSON parsing failed in task decomposition",
                error=str(e),
                response=response_content[:200] if "response_content" in locals() else "N/A",
            )
            return self._create_fallback_task_tree(requirements)
        except Exception as e:
            logger.error("Task decomposition failed", error=str(e))
            return self._create_fallback_task_tree(requirements)

    async def design_architecture(self, task_tree: Dict[str, Any]) -> Dict[str, Any]:
        """
        Design workflow architecture based on task tree
        """
        logger.info("Starting architecture design", task_count=len(task_tree.get("subtasks", [])))

        # Match tasks to architecture patterns
        pattern_match = self._match_architecture_pattern(task_tree)

        # Generate node mappings
        node_mappings = await self._generate_node_mappings(task_tree, pattern_match)

        # Design data flow
        data_flow = self._design_data_flow(node_mappings, task_tree)

        # Add error handling
        error_handling = self._design_error_handling(node_mappings)

        # Create final architecture
        architecture = {
            "pattern_used": pattern_match["pattern_name"],
            "nodes": node_mappings,
            "connections": self._generate_connections(node_mappings, task_tree),
            "data_flow": data_flow,
            "error_handling": error_handling,
            "performance_considerations": self._analyze_performance_considerations(node_mappings),
        }

        logger.info(
            "Architecture design completed",
            pattern=pattern_match["pattern_name"],
            node_count=len(node_mappings),
        )

        return architecture

    async def generate_optimizations(self, architecture: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate optimization suggestions for architecture
        """
        optimizations = []

        # Performance optimizations
        perf_opts = self._analyze_performance_optimizations(architecture)
        optimizations.extend(perf_opts)

        # Reliability optimizations
        rel_opts = self._analyze_reliability_optimizations(architecture)
        optimizations.extend(rel_opts)

        # Cost optimizations
        cost_opts = self._analyze_cost_optimizations(architecture)
        optimizations.extend(cost_opts)

        # Maintainability optimizations
        maint_opts = self._analyze_maintainability_optimizations(architecture)
        optimizations.extend(maint_opts)

        # Sort by impact and priority
        optimizations.sort(key=lambda x: (x["priority"], -x["impact_score"]), reverse=True)

        return optimizations[:10]  # Return top 10 optimizations

    def select_design_patterns(self, architecture: Dict[str, Any]) -> List[str]:
        """
        Select appropriate design patterns for architecture
        """
        patterns = []
        nodes = architecture.get("nodes", [])

        # Analyze node types and relationships
        node_types = [node.get("type", "") for node in nodes]

        # Pattern detection
        if any("AI_" in nt for nt in node_types):
            patterns.append("AI_Pipeline_Pattern")

        if any("FLOW_IF" in nt for nt in node_types):
            patterns.append("Conditional_Routing_Pattern")

        if any("EXTERNAL_" in nt for nt in node_types):
            patterns.append("External_Integration_Pattern")

        if any("MEMORY_" in nt for nt in node_types):
            patterns.append("State_Management_Pattern")

        # Add error handling patterns
        if architecture.get("error_handling"):
            patterns.append("Error_Recovery_Pattern")

        return patterns

    async def estimate_performance(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate performance characteristics of architecture
        """
        nodes = architecture.get("nodes", [])

        # Calculate resource usage
        total_cpu = sum(
            self.performance_models["node_costs"].get(node.get("type", ""), {}).get("cpu", 0.1)
            for node in nodes
        )
        total_memory = sum(
            self.performance_models["node_costs"].get(node.get("type", ""), {}).get("memory", 0.05)
            for node in nodes
        )

        # Estimate execution time (considering parallel opportunities)
        critical_path_time = self._calculate_critical_path_time(architecture)

        # Calculate throughput
        bottleneck_time = max(
            self.performance_models["node_costs"].get(node.get("type", ""), {}).get("time", 1)
            for node in nodes
        )
        estimated_throughput = 3600 / bottleneck_time  # requests per hour

        # Reliability estimation
        reliability_score = self._calculate_reliability_score(architecture)

        return {
            "avg_execution_time": f"{critical_path_time:.1f}秒",
            "throughput": f"{estimated_throughput:.0f}次/小时",
            "resource_usage": {
                "cpu_units": f"{total_cpu:.2f}",
                "memory_mb": f"{total_memory * 100:.0f}MB",
            },
            "reliability_score": reliability_score,
            "scalability": self._assess_scalability(architecture),
            "bottlenecks": self._identify_bottlenecks(architecture),
        }

    async def generate_dsl(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate workflow DSL from architecture
        """
        logger.info("Starting DSL generation")

        # Generate nodes
        dsl_nodes = []
        for node in architecture.get("nodes", []):
            dsl_node = self._convert_node_to_dsl(node)
            dsl_nodes.append(dsl_node)

        # Generate connections
        dsl_connections = self._convert_connections_to_dsl(architecture.get("connections", []))

        # Generate settings
        dsl_settings = self._generate_dsl_settings(architecture)

        # Create complete DSL
        workflow_dsl = {
            "version": "1.0.0",
            "metadata": {
                "name": "Generated Workflow",
                "description": "Auto-generated workflow from intelligent design",
                "pattern": architecture.get("pattern_used", "custom"),
                "created_at": datetime.now().isoformat(),
                "estimated_performance": architecture.get("performance_estimate", {}),
            },
            "nodes": dsl_nodes,
            "connections": dsl_connections,
            "settings": dsl_settings,
            "error_handling": architecture.get("error_handling", {}),
            "optimizations": architecture.get("optimizations", []),
        }

        logger.info("DSL generation completed", node_count=len(dsl_nodes))
        return workflow_dsl

    # Helper methods
    def _validate_task_tree(self, task_tree: Dict[str, Any]) -> Dict[str, Any]:
        """Validate task tree structure"""
        if "root_task" not in task_tree:
            task_tree["root_task"] = "Main workflow task"

        if "subtasks" not in task_tree:
            task_tree["subtasks"] = []

        if "dependencies" not in task_tree:
            task_tree["dependencies"] = []

        if "parallel_opportunities" not in task_tree:
            task_tree["parallel_opportunities"] = []

        return task_tree

    def _enhance_task_tree(
        self, task_tree: Dict[str, Any], requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance task tree with additional metadata"""
        # Add criticality analysis
        for task in task_tree.get("subtasks", []):
            if task.get("name", "").lower() in ["trigger", "input", "output"]:
                task["critical_path"] = True
            else:
                task["critical_path"] = False

        # Add resource estimates
        for task in task_tree.get("subtasks", []):
            task["resource_estimate"] = self._estimate_task_resources(task)

        return task_tree

    def _create_fallback_task_tree(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback task tree when LLM fails"""
        return {
            "root_task": requirements.get("primary_goal", "Workflow execution"),
            "subtasks": [
                {
                    "id": "input_task",
                    "name": "Input Processing",
                    "description": "Process input data",
                    "type": "sequential",
                    "dependencies": [],
                    "estimated_complexity": 3,
                    "critical_path": True,
                },
                {
                    "id": "main_task",
                    "name": "Main Processing",
                    "description": "Execute main workflow logic",
                    "type": "sequential",
                    "dependencies": ["input_task"],
                    "estimated_complexity": 5,
                    "critical_path": True,
                },
                {
                    "id": "output_task",
                    "name": "Output Generation",
                    "description": "Generate and deliver output",
                    "type": "sequential",
                    "dependencies": ["main_task"],
                    "estimated_complexity": 2,
                    "critical_path": True,
                },
            ],
            "dependencies": [
                {"from": "input_task", "to": "main_task", "type": "sequential"},
                {"from": "main_task", "to": "output_task", "type": "sequential"},
            ],
            "parallel_opportunities": [],
        }

    def _match_architecture_pattern(self, task_tree: Dict[str, Any]) -> Dict[str, Any]:
        """Match task tree to architecture patterns"""
        # Simple pattern matching logic
        subtasks = task_tree.get("subtasks", [])
        task_names = [task.get("name", "").lower() for task in subtasks]

        # Check for customer service pattern
        if any(
            keyword in " ".join(task_names)
            for keyword in ["email", "customer", "response", "support"]
        ):
            return {
                "pattern_name": "customer_service_automation",
                "confidence": 0.8,
                "pattern_data": self.pattern_library["customer_service_automation"],
            }

        # Check for data integration pattern
        if any(
            keyword in " ".join(task_names)
            for keyword in ["data", "extract", "transform", "integration"]
        ):
            return {
                "pattern_name": "data_integration_pipeline",
                "confidence": 0.7,
                "pattern_data": self.pattern_library["data_integration_pipeline"],
            }

        # Default to generic pattern
        return {
            "pattern_name": "generic_workflow",
            "confidence": 0.5,
            "pattern_data": {
                "pattern": "Sequential → Processing → Output",
                "nodes": [
                    {"type": "TRIGGER_MANUAL", "role": "trigger"},
                    {"type": "ACTION_NODE", "role": "processing"},
                    {"type": "EXTERNAL_API", "role": "output"},
                ],
            },
        }

    async def _generate_node_mappings(
        self, task_tree: Dict[str, Any], pattern_match: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate enhanced node mappings using RAG recommendations"""
        nodes = []
        pattern_nodes = pattern_match["pattern_data"].get("nodes", [])
        subtasks = task_tree.get("subtasks", [])

        # Map tasks to nodes with RAG enhancement
        for i, task in enumerate(subtasks):
            # Get RAG suggestions for this specific task
            task_description = f"{task.get('name', '')}: {task.get('description', '')}"
            rag_suggestions = await self.rag.get_node_type_suggestions(
                task_description, existing_nodes=[n.get("type") for n in nodes]
            )

            # Select appropriate node type (RAG-enhanced)
            node_type = self._select_node_type_enhanced(task, pattern_nodes, rag_suggestions)

            # Get RAG-enhanced parameters
            enhanced_params = await self._generate_enhanced_parameters(
                task, node_type, rag_suggestions
            )

            node = {
                "id": f"node_{i+1}",
                "name": task.get("name", f"Node {i+1}"),
                "type": node_type,
                "task_id": task.get("id"),
                "description": task.get("description", ""),
                "parameters": enhanced_params,
                "position": {"x": 100 + i * 200, "y": 100},
                "metadata": {
                    "complexity": task.get("estimated_complexity", 5),
                    "critical_path": task.get("critical_path", False),
                    "rag_confidence": self._get_rag_confidence(rag_suggestions),
                    "rag_alternatives": [
                        s["node_type"] for s in rag_suggestions[1:3]
                    ],  # Alternative suggestions
                },
            }
            nodes.append(node)

        return nodes

    def _select_node_type(self, task: Dict[str, Any], pattern_nodes: List[Dict[str, Any]]) -> str:
        """Select appropriate node type for task"""
        task_name = task.get("name", "").lower()
        task_desc = task.get("description", "").lower()

        # Rule-based node type selection
        if any(keyword in task_name for keyword in ["trigger", "start", "input"]):
            if "email" in task_desc:
                return "TRIGGER_EMAIL"
            elif "webhook" in task_desc:
                return "TRIGGER_WEBHOOK"
            elif "schedule" in task_desc:
                return "TRIGGER_CRON"
            else:
                return "TRIGGER_MANUAL"

        elif any(keyword in task_name for keyword in ["analyze", "ai", "intelligence"]):
            return "AI_TASK_ANALYZER"

        elif any(keyword in task_name for keyword in ["route", "condition", "if"]):
            return "FLOW_IF"

        elif any(keyword in task_name for keyword in ["external", "api", "integration"]):
            return "EXTERNAL_API"

        elif any(keyword in task_name for keyword in ["store", "memory", "save"]):
            return "MEMORY_VECTOR_STORE"

        else:
            return "ACTION_NODE"

    def _generate_node_parameters(self, task: Dict[str, Any], node_type: str) -> Dict[str, Any]:
        """Generate parameters for node based on task and type"""
        base_params = {"name": task.get("name", ""), "description": task.get("description", "")}

        # Type-specific parameters
        if node_type == "TRIGGER_EMAIL":
            base_params.update(
                {"email_provider": "gmail", "check_interval": "*/5 * * * *", "folder": "INBOX"}
            )
        elif node_type == "AI_TASK_ANALYZER":
            base_params.update({"model": "gpt-4", "temperature": 0.1, "max_tokens": 1000})
        elif node_type == "FLOW_IF":
            base_params.update(
                {
                    "condition": "{{data.confidence}} > 0.7",
                    "true_branch": "continue",
                    "false_branch": "escalate",
                }
            )

        return base_params

    def _design_data_flow(
        self, nodes: List[Dict[str, Any]], task_tree: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Design data flow between nodes"""
        data_flow = {
            "input_schema": self._define_input_schema(nodes),
            "output_schema": self._define_output_schema(nodes),
            "intermediate_data": self._define_intermediate_data(nodes),
            "data_transformations": self._define_data_transformations(nodes),
        }
        return data_flow

    def _design_error_handling(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Design error handling strategy"""
        return {
            "global_error_policy": "STOP_WORKFLOW_ON_ERROR",
            "retry_policies": {
                "default": {"max_attempts": 3, "backoff": "exponential"},
                "external_api": {"max_attempts": 5, "backoff": "linear"},
            },
            "error_notification": {"enabled": True, "channels": ["email", "slack"]},
            "fallback_strategies": {
                "ai_analysis_failure": "use_rule_based_fallback",
                "external_api_failure": "queue_for_retry",
            },
        }

    def _generate_connections(
        self, nodes: List[Dict[str, Any]], task_tree: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate connections between nodes"""
        connections = []
        dependencies = task_tree.get("dependencies", [])

        # Map task dependencies to node connections
        node_map = {node["task_id"]: node["id"] for node in nodes if "task_id" in node}

        for dep in dependencies:
            from_task = dep.get("from")
            to_task = dep.get("to")

            if from_task in node_map and to_task in node_map:
                connection = {
                    "source": node_map[from_task],
                    "target": node_map[to_task],
                    "type": dep.get("type", "sequential"),
                    "condition": dep.get("condition"),
                    "data_mapping": self._generate_data_mapping(from_task, to_task),
                }
                connections.append(connection)

        return connections

    def _analyze_performance_considerations(self, nodes: List[Dict[str, Any]]) -> List[str]:
        """Analyze performance considerations"""
        considerations = []

        # Check for AI nodes
        ai_nodes = [n for n in nodes if "AI_" in n.get("type", "")]
        if len(ai_nodes) > 1:
            considerations.append("多个AI节点可能导致延迟累积，考虑并行处理")

        # Check for external integrations
        external_nodes = [n for n in nodes if "EXTERNAL_" in n.get("type", "")]
        if len(external_nodes) > 2:
            considerations.append("多个外部集成可能导致网络延迟，考虑连接池和缓存")

        # Check for memory operations
        memory_nodes = [n for n in nodes if "MEMORY_" in n.get("type", "")]
        if len(memory_nodes) > 0:
            considerations.append("内存操作需要考虑数据量大小和检索效率")

        return considerations

    def _analyze_performance_optimizations(
        self, architecture: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze performance optimization opportunities"""
        optimizations = []
        nodes = architecture.get("nodes", [])

        # Parallel processing opportunities
        sequential_nodes = [
            n for n in nodes if not n.get("metadata", {}).get("critical_path", False)
        ]
        if len(sequential_nodes) > 1:
            optimizations.append(
                {
                    "type": "performance",
                    "category": "parallelization",
                    "description": "将非关键路径节点并行执行",
                    "impact_score": 8,
                    "implementation_complexity": 4,
                    "priority": "high",
                }
            )

        # Caching opportunities
        ai_nodes = [n for n in nodes if "AI_" in n.get("type", "")]
        if len(ai_nodes) > 0:
            optimizations.append(
                {
                    "type": "performance",
                    "category": "caching",
                    "description": "为AI分析结果添加缓存机制",
                    "impact_score": 6,
                    "implementation_complexity": 3,
                    "priority": "medium",
                }
            )

        return optimizations

    def _analyze_reliability_optimizations(
        self, architecture: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze reliability optimization opportunities"""
        optimizations = []

        # Error handling improvements
        optimizations.append(
            {
                "type": "reliability",
                "category": "error_handling",
                "description": "添加智能重试和降级机制",
                "impact_score": 9,
                "implementation_complexity": 5,
                "priority": "high",
            }
        )

        # Health monitoring
        optimizations.append(
            {
                "type": "reliability",
                "category": "monitoring",
                "description": "添加节点健康监控和告警",
                "impact_score": 7,
                "implementation_complexity": 4,
                "priority": "medium",
            }
        )

        return optimizations

    def _analyze_cost_optimizations(self, architecture: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze cost optimization opportunities"""
        optimizations = []

        # Resource optimization
        optimizations.append(
            {
                "type": "cost",
                "category": "resource_optimization",
                "description": "优化AI模型调用频率和批处理",
                "impact_score": 6,
                "implementation_complexity": 3,
                "priority": "medium",
            }
        )

        return optimizations

    def _analyze_maintainability_optimizations(
        self, architecture: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze maintainability optimization opportunities"""
        optimizations = []

        # Configuration management
        optimizations.append(
            {
                "type": "maintainability",
                "category": "configuration",
                "description": "外部化配置参数便于维护",
                "impact_score": 5,
                "implementation_complexity": 2,
                "priority": "low",
            }
        )

        return optimizations

    def _calculate_critical_path_time(self, architecture: Dict[str, Any]) -> float:
        """Calculate critical path execution time"""
        nodes = architecture.get("nodes", [])
        critical_nodes = [n for n in nodes if n.get("metadata", {}).get("critical_path", False)]

        total_time = 0.0
        for node in critical_nodes:
            node_type = node.get("type", "")
            time_cost = self.performance_models["node_costs"].get(node_type, {}).get("time", 1.0)
            total_time += time_cost

        return max(total_time, 1.0)  # Minimum 1 second

    def _calculate_reliability_score(self, architecture: Dict[str, Any]) -> float:
        """Calculate overall reliability score"""
        nodes = architecture.get("nodes", [])
        error_handling = architecture.get("error_handling", {})

        # Base reliability
        base_score = 0.7

        # Bonus for error handling
        if error_handling.get("retry_policies"):
            base_score += 0.1

        if error_handling.get("fallback_strategies"):
            base_score += 0.1

        # Penalty for complex nodes
        ai_nodes = [n for n in nodes if "AI_" in n.get("type", "")]
        external_nodes = [n for n in nodes if "EXTERNAL_" in n.get("type", "")]

        complexity_penalty = (len(ai_nodes) * 0.02) + (len(external_nodes) * 0.01)

        return min(max(base_score - complexity_penalty, 0.5), 0.95)

    def _assess_scalability(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Assess scalability characteristics"""
        return {
            "horizontal_scaling": "支持多实例并行处理",
            "vertical_scaling": "可通过增加资源提升性能",
            "bottlenecks": self._identify_bottlenecks(architecture),
            "scaling_recommendations": ["添加负载均衡", "实现数据分片"],
        }

    def _identify_bottlenecks(self, architecture: Dict[str, Any]) -> List[str]:
        """Identify potential bottlenecks"""
        bottlenecks = []
        nodes = architecture.get("nodes", [])

        # AI processing bottlenecks
        ai_nodes = [n for n in nodes if "AI_" in n.get("type", "")]
        if len(ai_nodes) > 2:
            bottlenecks.append("AI处理节点可能成为性能瓶颈")

        # External API bottlenecks
        external_nodes = [n for n in nodes if "EXTERNAL_" in n.get("type", "")]
        if len(external_nodes) > 1:
            bottlenecks.append("外部API调用可能限制整体吞吐量")

        return bottlenecks

    def _convert_node_to_dsl(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Convert node to DSL format"""
        return {
            "id": node.get("id"),
            "name": node.get("name"),
            "type": node.get("type"),
            "position": node.get("position", {"x": 0, "y": 0}),
            "parameters": node.get("parameters", {}),
            "metadata": node.get("metadata", {}),
        }

    def _convert_connections_to_dsl(self, connections: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert connections to DSL format"""
        dsl_connections = {}

        for conn in connections:
            source = conn.get("source")
            target = conn.get("target")

            if source and target:
                if source not in dsl_connections:
                    dsl_connections[source] = {}

                if "main" not in dsl_connections[source]:
                    dsl_connections[source]["main"] = []

                dsl_connections[source]["main"].append(
                    {"node": target, "type": conn.get("type", "main"), "index": 0}
                )

        return dsl_connections

    def _generate_dsl_settings(self, architecture: Dict[str, Any]) -> Dict[str, Any]:
        """Generate DSL settings"""
        return {
            "timezone": {"default": "UTC"},
            "save_execution_progress": True,
            "save_manual_executions": True,
            "timeout": 300,
            "error_policy": "STOP_WORKFLOW",
            "caller_policy": "WORKFLOW_MAIN",
        }

    def _estimate_task_resources(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate resource requirements for task"""
        complexity = task.get("estimated_complexity", 5)

        return {
            "cpu_units": complexity * 0.1,
            "memory_mb": complexity * 10,
            "estimated_duration": f"{complexity}秒",
        }

    def _define_input_schema(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Define input schema for workflow"""
        trigger_nodes = [n for n in nodes if "TRIGGER_" in n.get("type", "")]

        if trigger_nodes:
            # Base schema on trigger type
            trigger_type = trigger_nodes[0].get("type", "")
            if trigger_type == "TRIGGER_EMAIL":
                return {
                    "type": "object",
                    "properties": {
                        "email": {"type": "object"},
                        "subject": {"type": "string"},
                        "body": {"type": "string"},
                        "sender": {"type": "string"},
                    },
                }

        return {"type": "object", "properties": {}}

    def _define_output_schema(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Define output schema for workflow"""
        return {
            "type": "object",
            "properties": {
                "result": {"type": "object"},
                "status": {"type": "string"},
                "metadata": {"type": "object"},
            },
        }

    def _define_intermediate_data(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Define intermediate data structures"""
        return {
            "analysis_result": {"type": "object"},
            "processed_data": {"type": "object"},
            "decision_context": {"type": "object"},
        }

    def _define_data_transformations(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Define data transformations between nodes"""
        return [
            {"from": "input", "to": "analysis", "transformation": "extract_key_fields"},
            {"from": "analysis", "to": "decision", "transformation": "format_for_routing"},
        ]

    def _select_node_type_enhanced(
        self,
        task: Dict[str, Any],
        pattern_nodes: List[Dict[str, Any]],
        rag_suggestions: List[Dict[str, Any]],
    ) -> str:
        """Enhanced node type selection using RAG suggestions"""
        # Start with rule-based selection
        base_node_type = self._select_node_type(task, pattern_nodes)

        # If we have good RAG suggestions, consider them
        if rag_suggestions and rag_suggestions[0]["confidence"] in ["high", "medium"]:
            rag_node_type = rag_suggestions[0]["node_type"]

            # Prefer RAG suggestion if it's high confidence
            if rag_suggestions[0]["confidence"] == "high":
                logger.info(
                    "Using RAG node type suggestion",
                    task=task.get("name"),
                    base_type=base_node_type,
                    rag_type=rag_node_type,
                    confidence=rag_suggestions[0]["confidence"],
                )
                return rag_node_type

            # For medium confidence, use RAG if it's different and more specific
            if rag_node_type != base_node_type and len(rag_node_type) > len(base_node_type):
                return rag_node_type

        return base_node_type

    async def _generate_enhanced_parameters(
        self, task: Dict[str, Any], node_type: str, rag_suggestions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate enhanced parameters using RAG insights"""
        # Start with base parameters
        base_params = self._generate_node_parameters(task, node_type)

        # Find matching RAG suggestion
        matching_suggestion = None
        for suggestion in rag_suggestions:
            if suggestion["node_type"] == node_type:
                matching_suggestion = suggestion
                break

        if matching_suggestion:
            # Add RAG-specific configuration hints
            rag_metadata = matching_suggestion.get("metadata", {})

            if "configuration_hints" in rag_metadata:
                base_params.update(rag_metadata["configuration_hints"])

            if "best_practices" in rag_metadata:
                base_params["_rag_best_practices"] = rag_metadata["best_practices"]

            if "example_config" in rag_metadata:
                # Merge example configuration
                example_config = rag_metadata["example_config"]
                for key, value in example_config.items():
                    if key not in base_params:
                        base_params[key] = value

        return base_params

    def _get_rag_confidence(self, rag_suggestions: List[Dict[str, Any]]) -> str:
        """Get overall confidence from RAG suggestions"""
        if not rag_suggestions:
            return "none"

        top_suggestion = rag_suggestions[0]
        return top_suggestion.get("confidence", "low")

    def _generate_data_mapping(self, from_task: str, to_task: str) -> Dict[str, Any]:
        """Generate data mapping between tasks"""
        return {
            "input_mapping": f"output.{from_task}",
            "output_mapping": f"input.{to_task}",
            "transformations": [],
        }


class WorkflowOrchestrator:
    """
    Workflow orchestration engine that manages the complete MVP workflow
    Coordinates between IntelligentAnalyzer, IntelligentNegotiator, and IntelligentDesigner
    """

    def __init__(self):
        from core.intelligence import IntelligentAnalyzer, IntelligentNegotiator

        self.analyzer = IntelligentAnalyzer()
        self.negotiator = IntelligentNegotiator()
        self.designer = IntelligentDesigner()
        self.state_store = {}  # In-memory state store for MVP

    async def initialize_session(
        self, user_input: str, user_id: str = None, session_id: str = None
    ) -> Dict[str, Any]:
        """Initialize a new workflow generation session"""
        if not session_id:
            session_id = f"session_{datetime.now().timestamp()}"

        # Create initial state
        initial_state = {
            "metadata": {
                "session_id": session_id,
                "user_id": user_id or "anonymous",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "version": "1.0.0",
                "interaction_count": 0,
            },
            "stage": "requirement_negotiation",
            "requirement_negotiation": {
                "original_requirements": user_input,
                "parsed_intent": {},
                "capability_analysis": {},
                "identified_constraints": [],
                "proposed_solutions": [],
                "user_decisions": [],
                "negotiation_history": [],
                "final_requirements": "",
                "confidence_score": 0.0,
            },
            "design_state": {
                "task_tree": {},
                "architecture": {},
                "workflow_dsl": {},
                "optimization_suggestions": [],
                "design_patterns_used": [],
                "estimated_performance": {},
            },
            "configuration_state": {
                "current_node_index": 0,
                "node_configurations": [],
                "missing_parameters": [],
                "validation_results": [],
                "configuration_templates": [],
                "auto_filled_params": [],
            },
            "execution_state": {
                "preview_results": [],
                "static_validation": {},
                "configuration_completeness": {},
            },
        }

        # Store state
        self.state_store[session_id] = initial_state

        # Start with requirement analysis
        analysis_result = await self.analyzer.parse_requirements(user_input)
        capability_analysis = await self.analyzer.perform_capability_scan(analysis_result)

        # Update state
        initial_state["requirement_negotiation"]["parsed_intent"] = analysis_result
        initial_state["requirement_negotiation"]["capability_analysis"] = capability_analysis

        await self.save_session_state(initial_state)

        logger.info("Session initialized", session_id=session_id, stage=initial_state["stage"])

        return initial_state

    async def process_stage_transition(self, session_id: str, user_input: str) -> Dict[str, Any]:
        """Process input and transition between stages"""
        state = self.state_store.get(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")

        current_stage = state["stage"]
        state["metadata"]["interaction_count"] += 1
        state["metadata"]["updated_at"] = datetime.now()

        if current_stage == "requirement_negotiation":
            return await self._process_negotiation_stage(state, user_input)
        elif current_stage == "design":
            return await self._process_design_stage(state, user_input)
        elif current_stage == "configuration":
            return await self._process_configuration_stage(state, user_input)
        else:
            raise ValueError(f"Unknown stage: {current_stage}")

    async def _process_negotiation_stage(
        self, state: Dict[str, Any], user_input: str
    ) -> Dict[str, Any]:
        """Process negotiation stage"""
        capability_analysis = state["requirement_negotiation"]["capability_analysis"]
        negotiation_history = state["requirement_negotiation"]["negotiation_history"]

        # Add original requirements to capability analysis context
        negotiation_context = capability_analysis.copy()
        negotiation_context["original_requirements"] = state["requirement_negotiation"][
            "original_requirements"
        ]

        # Process negotiation round
        negotiation_result = await self.negotiator.process_negotiation_round(
            user_input, negotiation_context, negotiation_history
        )

        # Update negotiation history
        negotiation_step = {
            "question": negotiation_result.get("original_question", ""),
            "user_response": user_input,
            "analysis": negotiation_result.get("analysis", {}),
            "recommendations": negotiation_result.get("recommendations", []),
            "timestamp": datetime.now(),
        }
        state["requirement_negotiation"]["negotiation_history"].append(negotiation_step)

        # Check if negotiation is complete
        if negotiation_result.get("negotiation_complete", False):
            # Transition to design stage
            state["stage"] = "design"
            state["requirement_negotiation"]["final_requirements"] = negotiation_result.get(
                "final_requirements", ""
            )
            state["requirement_negotiation"]["confidence_score"] = negotiation_result.get(
                "confidence_score", 0.8
            )

            # Start design process
            return await self._start_design_process(state)
        else:
            # Continue negotiation
            await self.save_session_state(state)
            return {
                "stage": "requirement_negotiation",
                "next_questions": negotiation_result.get("next_questions", []),
                "tradeoff_analysis": negotiation_result.get("tradeoff_analysis"),
                "state": state,
            }

    async def _start_design_process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Start the design process"""
        final_requirements = state["requirement_negotiation"]["final_requirements"]
        user_decisions = state["requirement_negotiation"]["user_decisions"]

        # Convert to requirements format for designer
        requirements = {
            "primary_goal": final_requirements,
            "secondary_goals": [],
            "constraints": [
                c["description"] for c in state["requirement_negotiation"]["identified_constraints"]
            ],
            "user_decisions": user_decisions,
        }

        # Generate task tree
        task_tree = await self.designer.decompose_to_task_tree(requirements)
        state["design_state"]["task_tree"] = task_tree

        # Design architecture
        architecture = await self.designer.design_architecture(task_tree)
        state["design_state"]["architecture"] = architecture

        # Generate optimizations
        optimizations = await self.designer.generate_optimizations(architecture)
        state["design_state"]["optimization_suggestions"] = optimizations

        # Estimate performance
        performance_estimate = await self.designer.estimate_performance(architecture)
        state["design_state"]["estimated_performance"] = performance_estimate

        # Generate DSL
        workflow_dsl = await self.designer.generate_dsl(architecture)
        state["design_state"]["workflow_dsl"] = workflow_dsl

        # Select design patterns
        design_patterns = self.designer.select_design_patterns(architecture)
        state["design_state"]["design_patterns_used"] = design_patterns

        await self.save_session_state(state)

        return {
            "stage": "design",
            "task_tree": task_tree,
            "architecture": architecture,
            "workflow_dsl": workflow_dsl,
            "optimization_suggestions": optimizations,
            "performance_estimate": performance_estimate,
            "design_patterns": design_patterns,
            "state": state,
        }

    async def _process_design_stage(self, state: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        """Process design stage feedback"""
        # For MVP, assume user confirms design and move to configuration
        state["stage"] = "configuration"

        # Initialize configuration state
        architecture = state["design_state"]["architecture"]
        nodes = architecture.get("nodes", [])

        for i, node in enumerate(nodes):
            node_config = {
                "node_id": node.get("id"),
                "node_type": node.get("type"),
                "parameters": node.get("parameters", {}),
                "validation_status": "pending",
            }
            state["configuration_state"]["node_configurations"].append(node_config)

        await self.save_session_state(state)

        return {
            "stage": "configuration",
            "node_configurations": state["configuration_state"]["node_configurations"],
            "state": state,
        }

    async def _process_configuration_stage(
        self, state: Dict[str, Any], user_input: str
    ) -> Dict[str, Any]:
        """Process configuration stage"""
        # For MVP, perform static validation and complete
        workflow_dsl = state["design_state"]["workflow_dsl"]

        # Static validation
        validation_result = await self._perform_static_validation(workflow_dsl)
        state["execution_state"]["static_validation"] = validation_result

        # Configuration completeness check
        completeness_check = await self._check_configuration_completeness(state)
        state["execution_state"]["configuration_completeness"] = completeness_check

        # Mark as complete
        state["stage"] = "completed"

        await self.save_session_state(state)

        return {
            "stage": "completed",
            "workflow_dsl": workflow_dsl,
            "validation_result": validation_result,
            "completeness_check": completeness_check,
            "state": state,
        }

    async def _perform_static_validation(self, workflow_dsl: Dict[str, Any]) -> Dict[str, Any]:
        """Perform static validation of workflow DSL"""
        validation_result = {
            "syntax_valid": True,
            "logic_valid": True,
            "completeness_score": 0.9,
            "issues": [],
        }

        # Basic syntax validation
        required_fields = ["version", "nodes", "connections"]
        for field in required_fields:
            if field not in workflow_dsl:
                validation_result["syntax_valid"] = False
                validation_result["issues"].append(f"Missing required field: {field}")

        # Node validation
        nodes = workflow_dsl.get("nodes", [])
        if len(nodes) == 0:
            validation_result["logic_valid"] = False
            validation_result["issues"].append("Workflow must contain at least one node")

        # Connection validation
        connections = workflow_dsl.get("connections", {})
        if len(connections) == 0 and len(nodes) > 1:
            validation_result["logic_valid"] = False
            validation_result["issues"].append("Multi-node workflow must have connections")

        return validation_result

    async def _check_configuration_completeness(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Check configuration completeness"""
        node_configs = state["configuration_state"]["node_configurations"]

        missing_params = []
        invalid_params = []

        for config in node_configs:
            # Check for required parameters based on node type
            node_type = config.get("node_type", "")
            required_params = self._get_required_parameters(node_type)

            for param in required_params:
                if param not in config.get("parameters", {}):
                    missing_params.append(f"{config['node_id']}.{param}")

        completeness_percentage = max(0, 1 - (len(missing_params) * 0.1))

        return {
            "complete": len(missing_params) == 0,
            "missing_parameters": missing_params,
            "invalid_parameters": invalid_params,
            "completeness_percentage": completeness_percentage,
        }

    def _get_required_parameters(self, node_type: str) -> List[str]:
        """Get required parameters for node type"""
        required_params = {
            "TRIGGER_EMAIL": ["email_provider", "folder"],
            "AI_TASK_ANALYZER": ["model", "temperature"],
            "EXTERNAL_API": ["url", "method"],
            "FLOW_IF": ["condition"],
            "MEMORY_VECTOR_STORE": ["collection_name"],
        }

        return required_params.get(node_type, [])

    async def save_session_state(self, state: Dict[str, Any]) -> None:
        """Save session state (in-memory for MVP)"""
        session_id = state["metadata"]["session_id"]
        self.state_store[session_id] = state

        logger.debug("Session state saved", session_id=session_id, stage=state["stage"])

    def get_session_state(self, session_id: str) -> Dict[str, Any]:
        """Get session state"""
        return self.state_store.get(session_id)

    async def handle_decision_point(self, state: Dict[str, Any], decision: Dict[str, Any]) -> str:
        """Handle decision points in workflow"""
        current_stage = state["stage"]

        if current_stage == "requirement_negotiation":
            # Check if we have enough information to proceed
            capability_analysis = state["requirement_negotiation"]["capability_analysis"]
            if len(capability_analysis.get("capability_gaps", [])) == 0:
                return "design"
            else:
                return "requirement_negotiation"

        elif current_stage == "design":
            # For MVP, always proceed to configuration
            return "configuration"

        elif current_stage == "configuration":
            # Check if configuration is complete
            completeness = state["execution_state"].get("configuration_completeness", {})
            if completeness.get("complete", False):
                return "completed"
            else:
                return "configuration"

        return current_stage

    def validate_state_transition(
        self, from_stage: str, to_stage: str, context: Dict[str, Any]
    ) -> bool:
        """Validate if state transition is allowed"""
        valid_transitions = {
            "requirement_negotiation": ["design"],
            "design": ["configuration", "requirement_negotiation"],
            "configuration": ["completed", "design"],
            "completed": [],
        }

        return to_stage in valid_transitions.get(from_stage, [])


# Additional helper functions for DSL validation
class DSLValidator:
    """Static DSL validation utilities"""

    @staticmethod
    async def validate_syntax(dsl: Dict[str, Any]) -> Dict[str, Any]:
        """Validate DSL syntax"""
        errors = []
        warnings = []

        # Required top-level fields
        required_fields = ["version", "nodes", "connections", "settings"]
        for field in required_fields:
            if field not in dsl:
                errors.append(f"Missing required field: {field}")

        # Validate nodes
        nodes = dsl.get("nodes", [])
        if not isinstance(nodes, list):
            errors.append("'nodes' must be an array")
        else:
            for i, node in enumerate(nodes):
                if not isinstance(node, dict):
                    errors.append(f"Node {i} must be an object")
                    continue

                # Required node fields
                node_required = ["id", "name", "type"]
                for field in node_required:
                    if field not in node:
                        errors.append(f"Node {i} missing required field: {field}")

        # Validate connections
        connections = dsl.get("connections", {})
        if not isinstance(connections, dict):
            errors.append("'connections' must be an object")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    @staticmethod
    async def validate_logic(dsl: Dict[str, Any]) -> Dict[str, Any]:
        """Validate DSL logic"""
        errors = []
        warnings = []

        nodes = dsl.get("nodes", [])
        connections = dsl.get("connections", {})

        # Check for orphaned nodes
        node_ids = {node.get("id") for node in nodes if node.get("id")}
        connected_nodes = set()

        for source, targets in connections.items():
            connected_nodes.add(source)
            for target_list in targets.values():
                for target in target_list:
                    if isinstance(target, dict) and "node" in target:
                        connected_nodes.add(target["node"])

        orphaned = node_ids - connected_nodes
        if orphaned and len(nodes) > 1:
            warnings.append(f"Orphaned nodes detected: {', '.join(orphaned)}")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    @staticmethod
    async def calculate_completeness_score(dsl: Dict[str, Any]) -> float:
        """Calculate completeness score for DSL"""
        score = 0.0
        max_score = 1.0

        # Basic structure (40%)
        if dsl.get("nodes"):
            score += 0.2
        if dsl.get("connections"):
            score += 0.2

        # Node completeness (40%)
        nodes = dsl.get("nodes", [])
        if nodes:
            complete_nodes = 0
            for node in nodes:
                if all(field in node for field in ["id", "name", "type", "parameters"]):
                    complete_nodes += 1
            score += (complete_nodes / len(nodes)) * 0.4

        # Settings and metadata (20%)
        if dsl.get("settings"):
            score += 0.1
        if dsl.get("metadata"):
            score += 0.1

        return min(score, max_score)
