"""
AI Agent Node Executor.

Handles AI agent operations like routing, task analysis, data integration, etc.
"""

import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseNodeExecutor, NodeExecutionContext, NodeExecutionResult, ExecutionStatus


class AIAgentNodeExecutor(BaseNodeExecutor):
    """Executor for AI_AGENT_NODE type."""
    
    def __init__(self):
        super().__init__()
        self.openai_client = None
        self._init_openai_client()
    
    def _init_openai_client(self):
        """Initialize OpenAI client."""
        try:
            api_key = self._get_openai_api_key()
            if api_key:
                # For now, just store the API key
                self.openai_api_key = api_key
                self.openai_client = None  # Will be initialized when needed
        except Exception as e:
            self.logger.warning(f"Failed to initialize OpenAI client: {e}")
    
    def _get_openai_api_key(self) -> Optional[str]:
        """Get OpenAI API key from environment or credentials."""
        import os
        # Try environment variable first
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            return api_key
        
        # Try from credentials (would be passed in context)
        return None
    
    def get_supported_subtypes(self) -> List[str]:
        """Get supported AI agent subtypes."""
        return [
            "ROUTER_AGENT",
            "TASK_ANALYZER", 
            "DATA_INTEGRATOR",
            "REPORT_GENERATOR"
        ]
    
    def validate(self, node: Any) -> List[str]:
        """Validate AI agent node configuration."""
        errors = []
        
        if not node.subtype:
            errors.append("AI Agent subtype is required")
            return errors
        
        subtype = node.subtype
        
        if subtype == "ROUTER_AGENT":
            errors.extend(self._validate_required_parameters(node, ["model", "system_prompt"]))
        
        elif subtype == "TASK_ANALYZER":
            errors.extend(self._validate_required_parameters(node, ["model", "analysis_type"]))
            analysis_type = node.parameters.get("analysis_type", "")
            if analysis_type not in ["requirement", "complexity", "dependency", "resource"]:
                errors.append(f"Invalid analysis type: {analysis_type}")
        
        elif subtype == "DATA_INTEGRATOR":
            errors.extend(self._validate_required_parameters(node, ["model", "integration_type"]))
            integration_type = node.parameters.get("integration_type", "")
            if integration_type not in ["merge", "transform", "validate", "enrich"]:
                errors.append(f"Invalid integration type: {integration_type}")
        
        elif subtype == "REPORT_GENERATOR":
            errors.extend(self._validate_required_parameters(node, ["model", "report_type"]))
            report_type = node.parameters.get("report_type", "")
            if report_type not in ["summary", "detailed", "executive", "technical"]:
                errors.append(f"Invalid report type: {report_type}")
        
        return errors
    
    def execute(self, context: NodeExecutionContext) -> NodeExecutionResult:
        """Execute AI agent node."""
        start_time = time.time()
        logs = []
        
        try:
            subtype = context.node.subtype
            logs.append(f"Executing AI agent node with subtype: {subtype}")
            
            if subtype == "ROUTER_AGENT":
                return self._execute_router_agent_sync(context, logs, start_time)
            elif subtype == "TASK_ANALYZER":
                return self._execute_task_analyzer_sync(context, logs, start_time)
            elif subtype == "DATA_INTEGRATOR":
                return self._execute_data_integrator_sync(context, logs, start_time)
            elif subtype == "REPORT_GENERATOR":
                return self._execute_report_generator_sync(context, logs, start_time)
            else:
                return self._create_error_result(
                    f"Unsupported AI agent subtype: {subtype}",
                    execution_time=time.time() - start_time,
                    logs=logs
                )
        
        except Exception as e:
            return self._create_error_result(
                f"Error executing AI agent: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_router_agent_sync(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute router agent (synchronous version)."""
        model = context.get_parameter("model", "gpt-4")
        system_prompt = context.get_parameter("system_prompt", "You are a router agent that directs requests to appropriate handlers.")
        temperature = context.get_parameter("temperature", 0.7)
        max_tokens = context.get_parameter("max_tokens", 1000)
        
        logs.append(f"Router agent: {model}, temp: {temperature}")
        
        # Prepare input for routing
        input_text = self._prepare_input_for_ai(context.input_data)
        
        try:
            # For now, use mock response
            ai_response = self._mock_router_response(input_text)
            
            # Parse routing decision
            routing_decision = self._parse_routing_decision(ai_response)
            
            output_data = {
                "agent_type": "router",
                "model": model,
                "input_text": input_text,
                "ai_response": ai_response,
                "routing_decision": routing_decision,
                "confidence": routing_decision.get("confidence", 0.8),
                "next_handler": routing_decision.get("handler", "default"),
                "executed_at": datetime.now().isoformat()
            }
            
            return self._create_success_result(
                output_data=output_data,
                execution_time=time.time() - start_time,
                logs=logs
            )
            
        except Exception as e:
            return self._create_error_result(
                f"Error in router agent: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_task_analyzer_sync(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute task analyzer (synchronous version)."""
        model = context.get_parameter("model", "gpt-4")
        analysis_type = context.get_parameter("analysis_type", "requirement")
        temperature = context.get_parameter("temperature", 0.3)
        
        logs.append(f"Task analyzer: {model}, type: {analysis_type}")
        
        # Prepare input for analysis
        input_text = self._prepare_input_for_ai(context.input_data)
        
        system_prompt = self._get_analysis_prompt(analysis_type)
        
        try:
            # For now, use mock response
            ai_response = self._mock_analysis_response(analysis_type, input_text)
            
            # Parse analysis result
            analysis_result = self._parse_analysis_result(ai_response, analysis_type)
            
            output_data = {
                "agent_type": "task_analyzer",
                "analysis_type": analysis_type,
                "model": model,
                "input_text": input_text,
                "ai_response": ai_response,
                "analysis_result": analysis_result,
                "complexity_score": analysis_result.get("complexity_score", 5),
                "estimated_duration": analysis_result.get("estimated_duration", "1 hour"),
                "dependencies": analysis_result.get("dependencies", []),
                "executed_at": datetime.now().isoformat()
            }
            
            return self._create_success_result(
                output_data=output_data,
                execution_time=time.time() - start_time,
                logs=logs
            )
            
        except Exception as e:
            return self._create_error_result(
                f"Error in task analyzer: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_data_integrator_sync(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute data integrator (synchronous version)."""
        model = context.get_parameter("model", "gpt-4")
        integration_type = context.get_parameter("integration_type", "merge")
        temperature = context.get_parameter("temperature", 0.2)
        
        logs.append(f"Data integrator: {model}, type: {integration_type}")
        
        # Prepare data for integration
        data_sources = context.input_data.get("data_sources", [])
        integration_config = context.get_parameter("integration_config", {})
        
        try:
            # For now, use mock response
            ai_response = self._mock_integration_response(integration_type, data_sources)
            
            # Process integration result
            integrated_data = self._process_integration_result(ai_response, integration_type)
            
            output_data = {
                "agent_type": "data_integrator",
                "integration_type": integration_type,
                "model": model,
                "data_sources": data_sources,
                "integration_config": integration_config,
                "ai_response": ai_response,
                "integrated_data": integrated_data,
                "data_quality_score": integrated_data.get("quality_score", 0.9),
                "record_count": integrated_data.get("record_count", 0),
                "executed_at": datetime.now().isoformat()
            }
            
            return self._create_success_result(
                output_data=output_data,
                execution_time=time.time() - start_time,
                logs=logs
            )
            
        except Exception as e:
            return self._create_error_result(
                f"Error in data integrator: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _execute_report_generator_sync(self, context: NodeExecutionContext, logs: List[str], start_time: float) -> NodeExecutionResult:
        """Execute report generator (synchronous version)."""
        model = context.get_parameter("model", "gpt-4")
        report_type = context.get_parameter("report_type", "summary")
        temperature = context.get_parameter("temperature", 0.5)
        
        logs.append(f"Report generator: {model}, type: {report_type}")
        
        # Prepare data for report generation
        report_data = context.input_data.get("report_data", {})
        report_template = context.get_parameter("report_template", "")
        
        try:
            # For now, use mock response
            ai_response = self._mock_report_response(report_type, report_data)
            
            # Process report result
            report_content = self._process_report_result(ai_response, report_type)
            
            output_data = {
                "agent_type": "report_generator",
                "report_type": report_type,
                "model": model,
                "report_data": report_data,
                "report_template": report_template,
                "ai_response": ai_response,
                "report_content": report_content,
                "word_count": len(report_content.get("content", "").split()),
                "sections": report_content.get("sections", []),
                "executed_at": datetime.now().isoformat()
            }
            
            return self._create_success_result(
                output_data=output_data,
                execution_time=time.time() - start_time,
                logs=logs
            )
            
        except Exception as e:
            return self._create_error_result(
                f"Error in report generator: {str(e)}",
                error_details={"exception": str(e)},
                execution_time=time.time() - start_time,
                logs=logs
            )
    
    def _prepare_input_for_ai(self, input_data: Dict[str, Any]) -> str:
        """Prepare input data for AI processing."""
        if isinstance(input_data, str):
            return input_data
        
        # Convert dict to structured text
        if isinstance(input_data, dict):
            return json.dumps(input_data, indent=2, ensure_ascii=False)
        
        return str(input_data)
    
    def _get_analysis_prompt(self, analysis_type: str) -> str:
        """Get analysis prompt based on type."""
        prompts = {
            "requirement": "Analyze the requirements and extract key information, constraints, and dependencies.",
            "complexity": "Analyze the complexity of the task and provide difficulty assessment.",
            "dependency": "Identify dependencies and prerequisites for the task.",
            "resource": "Analyze resource requirements and estimate needed resources."
        }
        return prompts.get(analysis_type, "Analyze the provided information.")
    
    def _get_integration_prompt(self, integration_type: str, data_sources: List[Dict], config: Dict) -> str:
        """Get integration prompt."""
        return f"Integrate data from {len(data_sources)} sources using {integration_type} method. Config: {config}"
    
    def _get_report_prompt(self, report_type: str, data: Dict, template: str) -> str:
        """Get report generation prompt."""
        return f"Generate a {report_type} report based on the provided data. Template: {template}"
    
    def _mock_router_response(self, input_text: str) -> str:
        """Mock router response for testing."""
        return '{"handler": "default", "confidence": 0.8, "reason": "Standard routing"}'
    
    def _mock_analysis_response(self, analysis_type: str, input_text: str) -> str:
        """Mock analysis response for testing."""
        return f'{{"analysis_type": "{analysis_type}", "complexity_score": 5, "estimated_duration": "1 hour"}}'
    
    def _mock_integration_response(self, integration_type: str, data_sources: List[Dict]) -> str:
        """Mock integration response for testing."""
        return f'{{"integration_type": "{integration_type}", "record_count": {len(data_sources) * 10}}}'
    
    def _mock_report_response(self, report_type: str, data: Dict) -> str:
        """Mock report response for testing."""
        return f'{{"report_type": "{report_type}", "content": "Sample report content", "sections": ["summary", "details"]}}'
    
    def _parse_routing_decision(self, response: str) -> Dict[str, Any]:
        """Parse routing decision from AI response."""
        try:
            return json.loads(response)
        except:
            return {"handler": "default", "confidence": 0.5, "reason": "Fallback routing"}
    
    def _parse_analysis_result(self, response: str, analysis_type: str) -> Dict[str, Any]:
        """Parse analysis result from AI response."""
        try:
            return json.loads(response)
        except:
            return {
                "analysis_type": analysis_type,
                "complexity_score": 5,
                "estimated_duration": "1 hour",
                "dependencies": []
            }
    
    def _process_integration_result(self, response: str, integration_type: str) -> Dict[str, Any]:
        """Process integration result."""
        try:
            result = json.loads(response)
            result["quality_score"] = 0.9
            return result
        except:
            return {
                "integration_type": integration_type,
                "record_count": 0,
                "quality_score": 0.5
            }
    
    def _process_report_result(self, response: str, report_type: str) -> Dict[str, Any]:
        """Process report result."""
        try:
            result = json.loads(response)
            return result
        except:
            return {
                "report_type": report_type,
                "content": response,
                "sections": ["summary"]
            }
