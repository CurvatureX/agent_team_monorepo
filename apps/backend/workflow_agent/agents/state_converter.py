"""
State conversion utilities between protobuf AgentState and WorkflowState
"""

import json
import time
from typing import Dict, Any, List

from workflow_agent.proto import workflow_agent_pb2
from workflow_agent.agents.state import (
    WorkflowState, WorkflowStage, AlternativeOption, Conversation, 
    ClarificationContext, RAGContext, RetrievedDocument, 
    WorkflowOrigin, ClarificationPurpose
)


class StateConverter:
    """Convert between protobuf AgentState and internal WorkflowState"""

    @staticmethod
    def proto_to_workflow_state(proto_state: workflow_agent_pb2.AgentState) -> WorkflowState:
        """Convert protobuf AgentState to WorkflowState"""
        
        # Convert stage
        stage = StateConverter._proto_stage_to_internal(proto_state.stage)
        previous_stage = None
        if proto_state.previous_stage:
            previous_stage = StateConverter._proto_stage_to_internal(proto_state.previous_stage)

        # Convert conversations
        conversations = []
        for conv in proto_state.conversations:
            conversation = Conversation(
                role=conv.role,
                text=conv.text,
                timestamp=conv.timestamp,
                metadata=dict(conv.metadata)
            )
            conversations.append(conversation)

        # Convert alternatives
        alternatives = []
        for alt in proto_state.alternatives:
            alternative = AlternativeOption(
                id=alt.id,
                title=alt.title,
                description=alt.description,
                approach=alt.approach,
                trade_offs=list(alt.trade_offs),
                complexity=alt.complexity
            )
            alternatives.append(alternative)

        # Convert clarification context
        purpose = None
        if proto_state.clarification_context.purpose:
            purpose_map = {
                "initial_intent": ClarificationPurpose.INITIAL_INTENT,
                "template_modification": ClarificationPurpose.TEMPLATE_MODIFICATION,
                "gap_resolution": ClarificationPurpose.GAP_RESOLUTION
            }
            purpose = purpose_map.get(proto_state.clarification_context.purpose, ClarificationPurpose.INITIAL_INTENT)
        
        origin_map = {
            "create": WorkflowOrigin.CREATE,
            "edit": WorkflowOrigin.EDIT,
            "copy": WorkflowOrigin.COPY
        }
        origin = origin_map.get(proto_state.clarification_context.origin, WorkflowOrigin.CREATE)
        
        clarification_context = ClarificationContext(
            origin=origin,
            pending_questions=list(proto_state.clarification_context.pending_questions)
        )
        if purpose:
            clarification_context["purpose"] = purpose
        if proto_state.clarification_context.collected_info:
            clarification_context["collected_info"] = dict(proto_state.clarification_context.collected_info)

        # Convert workflow context
        workflow_context = {
            "origin": proto_state.workflow_context.origin,
            "source_workflow_id": proto_state.workflow_context.source_workflow_id,
            "modification_intent": proto_state.workflow_context.modification_intent
        }

        # Convert current_workflow from JSON
        current_workflow = {}
        if proto_state.current_workflow_json:
            try:
                current_workflow = json.loads(proto_state.current_workflow_json)
            except json.JSONDecodeError:
                current_workflow = {}

        # Convert RAG context
        rag_context = None
        if proto_state.rag_context:
            rag_results = []
            for result in proto_state.rag_context.results:
                rag_result = RetrievedDocument(
                    id=result.id,
                    content=result.content,
                    similarity=result.similarity
                )
                # 添加可选字段
                if result.node_type:
                    rag_result["node_type"] = result.node_type
                if result.title:
                    rag_result["title"] = result.title
                if result.description:
                    rag_result["description"] = result.description
                if result.metadata:
                    rag_result["metadata"] = dict(result.metadata)
                    
                rag_results.append(rag_result)
            
            rag_context = RAGContext(
                results=rag_results,
                query=proto_state.rag_context.query,
            )
            
            # 添加可选字段
            if proto_state.rag_context.timestamp:
                rag_context["timestamp"] = proto_state.rag_context.timestamp
            if proto_state.rag_context.metadata:
                rag_context["metadata"] = dict(proto_state.rag_context.metadata)

        # Build WorkflowState
        workflow_state = WorkflowState(
            session_id=proto_state.session_id,
            user_id=proto_state.user_id,
            created_at=proto_state.created_at,
            updated_at=proto_state.updated_at,
            stage=stage,
            execution_history=list(proto_state.execution_history),
            clarification_context=clarification_context,
            conversations=conversations,
            intent_summary=proto_state.intent_summary,
            gaps=list(proto_state.gaps),
            alternatives=alternatives,
            current_workflow=current_workflow,
            debug_result=proto_state.debug_result,
            debug_loop_count=proto_state.debug_loop_count,
            workflow_context=workflow_context
        )

        # Add optional fields
        if previous_stage:
            workflow_state["previous_stage"] = previous_stage
        if rag_context:
            workflow_state["rag"] = rag_context

        return workflow_state

    @staticmethod
    def workflow_state_to_proto(state: WorkflowState) -> workflow_agent_pb2.AgentState:
        """Convert WorkflowState to protobuf AgentState"""
        
        # Convert conversations
        conversations = []
        for conv in state.get("conversations", []):
            conversation = workflow_agent_pb2.Conversation(
                role=conv.get("role", ""),
                text=conv.get("text", ""),
                timestamp=conv.get("timestamp", int(time.time() * 1000)),
                metadata=conv.get("metadata", {})
            )
            conversations.append(conversation)

        # Convert alternatives
        alternatives = []
        for alt in state.get("alternatives", []):
            alternative = workflow_agent_pb2.AlternativeOption(
                id=alt.get("id", ""),
                title=alt.get("title", ""),
                description=alt.get("description", ""),
                approach=alt.get("approach", ""),
                trade_offs=alt.get("trade_offs", []),
                complexity=alt.get("complexity", "simple")
            )
            alternatives.append(alternative)

        # Convert clarification context
        clarification_ctx = state.get("clarification_context", {})
        
        # 处理origin字段 - 转换枚举值为字符串
        origin_str = "create"
        origin_value = clarification_ctx.get("origin")
        if isinstance(origin_value, WorkflowOrigin):
            origin_str = origin_value.value
        elif isinstance(origin_value, str):
            origin_str = origin_value
            
        # 处理purpose字段
        purpose_str = ""
        purpose_value = clarification_ctx.get("purpose")
        if isinstance(purpose_value, ClarificationPurpose):
            purpose_str = purpose_value.value
        elif isinstance(purpose_value, str):
            purpose_str = purpose_value
            
        clarification_context = workflow_agent_pb2.ClarificationContext(
            origin=origin_str,
            pending_questions=clarification_ctx.get("pending_questions", [])
        )
        
        if purpose_str:
            clarification_context.purpose = purpose_str
        collected_info = clarification_ctx.get("collected_info")
        if collected_info:
            clarification_context.collected_info.update(collected_info)

        # Convert workflow context
        workflow_ctx = state.get("workflow_context", {})
        workflow_context = workflow_agent_pb2.WorkflowContext(
            origin=workflow_ctx.get("origin", "create"),
            source_workflow_id=workflow_ctx.get("source_workflow_id", ""),
            modification_intent=workflow_ctx.get("modification_intent", "")
        )

        # Convert current_workflow to JSON
        current_workflow_json = ""
        if state.get("current_workflow"):
            try:
                current_workflow_json = json.dumps(state["current_workflow"])
            except (TypeError, ValueError):
                current_workflow_json = "{}"

        # Convert RAG context
        rag_context = None
        rag_data = state.get("rag")
        if rag_data:
            rag_results = []
            
            results_data = rag_data.get("results", [])
            
            for result in results_data:
                rag_result = workflow_agent_pb2.RAGResult(
                    id=result.get("id", ""),
                    content=result.get("content", ""),
                    similarity=result.get("similarity", 0.0)
                )
                
                # 添加可选字段
                node_type = result.get("node_type")
                if node_type:
                    rag_result.node_type = node_type
                title = result.get("title")
                if title:
                    rag_result.title = title
                description = result.get("description")
                if description:
                    rag_result.description = description
                metadata = result.get("metadata")
                if metadata:
                    rag_result.metadata.update(metadata)
                    
                rag_results.append(rag_result)
            
            query = rag_data.get("query", "")
            
            rag_context = workflow_agent_pb2.RAGContext(
                results=rag_results,
                query=query
            )
            
            # 添加可选字段
            timestamp = rag_data.get("timestamp")
            if timestamp:
                rag_context.timestamp = timestamp
            else:
                rag_context.timestamp = int(time.time() * 1000)
                
            rag_metadata = rag_data.get("metadata")
            if rag_metadata:
                rag_context.metadata.update(rag_metadata)

        # Build AgentState
        agent_state = workflow_agent_pb2.AgentState(
            session_id=state.get("session_id", ""),
            user_id=state.get("user_id", ""),
            created_at=state.get("created_at", int(time.time() * 1000)),
            updated_at=int(time.time() * 1000),
            stage=StateConverter._internal_stage_to_proto(state.get("stage", WorkflowStage.CLARIFICATION)),
            conversations=conversations,
            intent_summary=state.get("intent_summary", ""),
            gaps=state.get("gaps", []),
            alternatives=alternatives,
            current_workflow_json=current_workflow_json,
            debug_result=state.get("debug_result", ""),
            debug_loop_count=state.get("debug_loop_count", 0),
            clarification_context=clarification_context,
            workflow_context=workflow_context,
            execution_history=state.get("execution_history", [])
        )

        # Add optional fields
        previous_stage = state.get("previous_stage")
        if previous_stage:
            agent_state.previous_stage = StateConverter._internal_stage_to_proto(previous_stage)
        
        if rag_context:
            agent_state.rag_context.CopyFrom(rag_context)

        return agent_state

    @staticmethod
    def _proto_stage_to_internal(proto_stage: workflow_agent_pb2.WorkflowStage) -> WorkflowStage:
        """Convert protobuf WorkflowStage to internal WorkflowStage"""
        stage_mapping = {
            workflow_agent_pb2.STAGE_CLARIFICATION: WorkflowStage.CLARIFICATION,
            workflow_agent_pb2.STAGE_NEGOTIATION: WorkflowStage.NEGOTIATION,
            workflow_agent_pb2.STAGE_GAP_ANALYSIS: WorkflowStage.GAP_ANALYSIS,
            workflow_agent_pb2.STAGE_ALTERNATIVE_GENERATION: WorkflowStage.ALTERNATIVE_GENERATION,
            workflow_agent_pb2.STAGE_WORKFLOW_GENERATION: WorkflowStage.WORKFLOW_GENERATION,
            workflow_agent_pb2.STAGE_DEBUG: WorkflowStage.DEBUG,
            workflow_agent_pb2.STAGE_COMPLETED: WorkflowStage.COMPLETED,
            workflow_agent_pb2.STAGE_ERROR: WorkflowStage.CLARIFICATION,  # Default fallback
        }
        return stage_mapping.get(proto_stage, WorkflowStage.CLARIFICATION)

    @staticmethod
    def _internal_stage_to_proto(internal_stage: WorkflowStage) -> workflow_agent_pb2.WorkflowStage:
        """Convert internal WorkflowStage to protobuf WorkflowStage"""
        stage_mapping = {
            WorkflowStage.CLARIFICATION: workflow_agent_pb2.STAGE_CLARIFICATION,
            WorkflowStage.NEGOTIATION: workflow_agent_pb2.STAGE_NEGOTIATION,
            WorkflowStage.GAP_ANALYSIS: workflow_agent_pb2.STAGE_GAP_ANALYSIS,
            WorkflowStage.ALTERNATIVE_GENERATION: workflow_agent_pb2.STAGE_ALTERNATIVE_GENERATION,
            WorkflowStage.WORKFLOW_GENERATION: workflow_agent_pb2.STAGE_WORKFLOW_GENERATION,
            WorkflowStage.DEBUG: workflow_agent_pb2.STAGE_DEBUG,
            WorkflowStage.COMPLETED: workflow_agent_pb2.STAGE_COMPLETED,
        }
        return stage_mapping.get(internal_stage, workflow_agent_pb2.STAGE_ERROR)