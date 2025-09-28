"""
ANTHROPIC_CLAUDE AI Agent Node Specification

Anthropic Claude AI agent node for performing advanced AI operations including
text generation, analysis, reasoning, code generation, and multi-modal processing.
"""

from typing import Any, Dict, List

from ...models.node_enums import AIAgentSubtype, AnthropicModel, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class AnthropicClaudeSpec(BaseNodeSpec):
    """Anthropic Claude AI agent specification for advanced AI processing."""

    def __init__(self):
        super().__init__(
            type=NodeType.AI_AGENT,
            subtype=AIAgentSubtype.ANTHROPIC_CLAUDE,
            name="Anthropic_Claude",
            description="Anthropic Claude AI agent for advanced reasoning, analysis, code generation, and multi-modal processing",
            # Configuration parameters
            configurations={
                "anthropic_api_key": {
                    "type": "string",
                    "default": "",
                    "description": "Anthropic API密钥",
                    "required": True,
                    "sensitive": True,
                },
                "model": {
                    "type": "string",
                    "default": AnthropicModel.CLAUDE_SONNET_4.value,
                    "description": "Claude模型版本",
                    "required": True,
                    "options": [model.value for model in AnthropicModel],
                },
                "system_prompt": {
                    "type": "string",
                    "default": "",
                    "description": "系统提示词",
                    "required": False,
                    "multiline": True,
                },
                "user_prompt": {
                    "type": "string",
                    "default": "",
                    "description": "用户提示词模板",
                    "required": True,
                    "multiline": True,
                },
                "max_tokens": {
                    "type": "integer",
                    "default": 4096,
                    "min": 1,
                    "max": 200000,
                    "description": "最大输出令牌数",
                    "required": False,
                },
                "temperature": {
                    "type": "number",
                    "default": 0.7,
                    "min": 0.0,
                    "max": 1.0,
                    "description": "创造性温度参数",
                    "required": False,
                },
                "top_p": {
                    "type": "number",
                    "default": 0.9,
                    "min": 0.0,
                    "max": 1.0,
                    "description": "Top-p采样参数",
                    "required": False,
                },
                "top_k": {
                    "type": "integer",
                    "default": 40,
                    "min": 1,
                    "max": 100,
                    "description": "Top-k采样参数",
                    "required": False,
                },
                "stop_sequences": {
                    "type": "array",
                    "default": [],
                    "description": "停止序列",
                    "required": False,
                },
                "response_format": {
                    "type": "string",
                    "default": "text",
                    "description": "响应格式",
                    "required": False,
                    "options": ["text", "json", "structured", "markdown", "code"],
                },
                "thinking_mode": {
                    "type": "boolean",
                    "default": False,
                    "description": "是否启用思维模式（显示推理过程）",
                    "required": False,
                },
                "multimodal_config": {
                    "type": "object",
                    "default": {
                        "enable_vision": False,
                        "max_images": 5,
                        "image_detail": "auto",
                        "supported_formats": ["jpeg", "png", "gif", "webp"],
                    },
                    "description": "多模态配置",
                    "required": False,
                },
                "function_calling": {
                    "type": "object",
                    "default": {"enabled": False, "functions": [], "function_choice": "auto"},
                    "description": "函数调用配置",
                    "required": False,
                },
                "context_management": {
                    "type": "object",
                    "default": {
                        "enable_memory": False,
                        "memory_type": "conversation",
                        "max_context_length": 100000,
                        "context_compression": False,
                    },
                    "description": "上下文管理",
                    "required": False,
                },
                "output_processing": {
                    "type": "object",
                    "default": {
                        "enable_streaming": False,
                        "parse_json": False,
                        "extract_code": False,
                        "validate_output": False,
                        "output_schema": {},
                    },
                    "description": "输出处理配置",
                    "required": False,
                },
                "safety_config": {
                    "type": "object",
                    "default": {
                        "content_filtering": True,
                        "harmful_content_detection": True,
                        "pii_detection": False,
                        "custom_safety_guidelines": "",
                    },
                    "description": "安全配置",
                    "required": False,
                },
                "performance_config": {
                    "type": "object",
                    "default": {
                        "timeout_seconds": 120,
                        "retry_attempts": 3,
                        "retry_delay": 1.0,
                        "exponential_backoff": True,
                        "cache_responses": False,
                    },
                    "description": "性能配置",
                    "required": False,
                },
                "cost_optimization": {
                    "type": "object",
                    "default": {
                        "enable_caching": False,
                        "cache_ttl": 3600,
                        "prompt_compression": False,
                        "output_length_limit": -1,
                    },
                    "description": "成本优化配置",
                    "required": False,
                },
                **COMMON_CONFIGS,
            },
            # Default runtime parameters
            default_input_params={
                "user_input": "",
                "context": {},
                "variables": {},
                "images": [],
                "documents": [],
            },
            default_output_params={
                "response": "",
                "thinking_process": "",
                "confidence_score": 0.0,
                "token_usage": {},
                "processing_time": 0.0,
                "function_calls": [],
                "extracted_data": {},
                "safety_flags": {},
                "model_version": "",
                "request_id": "",
            },
            # Port definitions
            input_ports=[
                create_port(
                    port_id="main",
                    name="main",
                    data_type="dict",
                    description="Main input with user prompt and context",
                    required=True,
                    max_connections=1,
                ),
                create_port(
                    port_id="context",
                    name="context",
                    data_type="dict",
                    description="Additional context and variables",
                    required=False,
                    max_connections=1,
                ),
                create_port(
                    port_id="images",
                    name="images",
                    data_type="array",
                    description="Images for multi-modal processing",
                    required=False,
                    max_connections=1,
                ),
            ],
            output_ports=[
                create_port(
                    port_id="response",
                    name="response",
                    data_type="dict",
                    description="Claude's response and metadata",
                    required=True,
                    max_connections=-1,
                ),
                create_port(
                    port_id="structured_data",
                    name="structured_data",
                    data_type="dict",
                    description="Extracted structured data from response",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="function_results",
                    name="function_results",
                    data_type="array",
                    description="Results from function calls",
                    required=False,
                    max_connections=-1,
                ),
                create_port(
                    port_id="error",
                    name="error",
                    data_type="dict",
                    description="Error information if processing fails",
                    required=False,
                    max_connections=-1,
                ),
            ],
            # Metadata
            tags=["ai-agent", "anthropic", "claude", "llm", "reasoning", "analysis", "generation"],
            # Examples
            examples=[
                {
                    "name": "Advanced Code Analysis and Review",
                    "description": "Perform comprehensive code analysis with security, performance, and best practices review",
                    "configurations": {
                        "anthropic_api_key": "sk-ant-your_api_key_here",
                        "model": "claude-sonnet-4-20250514",
                        "system_prompt": "You are an expert software engineer and security analyst. Perform comprehensive code reviews focusing on:\n1. Code quality and best practices\n2. Security vulnerabilities\n3. Performance optimizations\n4. Maintainability improvements\n5. Testing recommendations\n\nProvide specific, actionable feedback with code examples.",
                        "user_prompt": "Please analyze the following code:\n\n**Language:** {{language}}\n**Context:** {{code_context}}\n**Code:**\n```{{language}}\n{{code_content}}\n```\n\nProvide a detailed analysis covering security, performance, maintainability, and suggestions for improvement.",
                        "max_tokens": 8192,
                        "temperature": 0.3,
                        "thinking_mode": True,
                        "response_format": "structured",
                        "output_processing": {
                            "parse_json": True,
                            "validate_output": True,
                            "output_schema": {
                                "type": "object",
                                "properties": {
                                    "overall_rating": {"type": "string"},
                                    "security_issues": {"type": "array"},
                                    "performance_issues": {"type": "array"},
                                    "best_practice_violations": {"type": "array"},
                                    "improvement_suggestions": {"type": "array"},
                                    "positive_aspects": {"type": "array"},
                                },
                            },
                        },
                    },
                    "input_example": {
                        "user_input": {
                            "language": "python",
                            "code_context": "FastAPI authentication middleware for a financial services API",
                            "code_content": 'def authenticate_user(token: str):\n    if not token:\n        return None\n    try:\n        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])\n        user_id = payload.get("user_id")\n        user = get_user_by_id(user_id)\n        return user\n    except:\n        return None',
                        },
                        "context": {
                            "project_type": "financial_api",
                            "security_level": "high",
                            "compliance_requirements": ["PCI-DSS", "SOX"],
                        },
                    },
                    "expected_outputs": {
                        "response": {
                            "response": "# Code Analysis Results\n\n## Overall Assessment\n**Rating:** Needs Significant Improvement\n\n## Critical Security Issues\n1. **Broad Exception Handling**: The bare `except:` clause masks all exceptions...",
                            "thinking_process": "Let me analyze this authentication code step by step:\n\n1. Security Analysis:\n   - The function uses JWT decoding which is good\n   - However, there's a bare except clause which is dangerous\n   - No input validation on the token\n   - SECRET_KEY appears to be a global variable...",
                            "confidence_score": 0.95,
                            "token_usage": {
                                "input_tokens": 245,
                                "output_tokens": 1580,
                                "total_tokens": 1825,
                                "cost_usd": 0.0234,
                            },
                            "processing_time": 3.2,
                            "model_version": "claude-sonnet-4-20250514",
                        },
                        "structured_data": {
                            "overall_rating": "Needs Significant Improvement",
                            "security_issues": [
                                {
                                    "type": "Exception Handling",
                                    "severity": "High",
                                    "description": "Bare except clause masks all exceptions, including security-critical JWT errors",
                                    "line_number": 8,
                                    "recommendation": "Use specific exception handling for JWT errors",
                                },
                                {
                                    "type": "Input Validation",
                                    "severity": "Medium",
                                    "description": "No validation of token format before processing",
                                    "recommendation": "Add token format validation",
                                },
                            ],
                            "performance_issues": [
                                {
                                    "type": "Database Query",
                                    "description": "get_user_by_id() called on every request without caching",
                                    "recommendation": "Implement user data caching with TTL",
                                }
                            ],
                            "improvement_suggestions": [
                                "Implement proper JWT exception handling",
                                "Add input validation and sanitization",
                                "Use structured logging for security events",
                                "Implement rate limiting for authentication attempts",
                            ],
                        },
                    },
                },
                {
                    "name": "Multi-Modal Document Analysis",
                    "description": "Analyze documents with both text and images for comprehensive insights",
                    "configurations": {
                        "anthropic_api_key": "sk-ant-your_api_key_here",
                        "model": "claude-sonnet-4-20250514",
                        "system_prompt": "You are an expert document analyst specializing in multi-modal content analysis. Analyze both textual content and visual elements in documents to provide comprehensive insights including:\n1. Content summarization\n2. Key data extraction\n3. Visual element analysis\n4. Document structure assessment\n5. Actionable insights and recommendations",
                        "user_prompt": "Analyze this document comprehensively:\n\n**Document Type:** {{document_type}}\n**Purpose:** {{analysis_purpose}}\n**Content:** {{text_content}}\n\nPlease provide:\n1. Executive summary\n2. Key findings and data points\n3. Visual elements analysis\n4. Recommendations based on the content\n5. Any concerns or red flags identified",
                        "max_tokens": 6144,
                        "temperature": 0.4,
                        "multimodal_config": {
                            "enable_vision": True,
                            "max_images": 3,
                            "image_detail": "high",
                        },
                        "output_processing": {"parse_json": True, "extract_code": False},
                    },
                    "input_example": {
                        "user_input": {
                            "document_type": "Financial Report",
                            "analysis_purpose": "Investment due diligence",
                            "text_content": "Q4 2024 Financial Results - Revenue increased 23% YoY to $156M. EBITDA margin improved to 18.5% from 14.2% in Q4 2023...",
                        },
                        "images": [
                            {
                                "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAA...",
                                "description": "Revenue growth chart showing quarterly performance",
                            },
                            {
                                "url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAA...",
                                "description": "Balance sheet summary with key financial ratios",
                            },
                        ],
                        "context": {
                            "investor_focus": "growth_potential",
                            "sector": "SaaS",
                            "market_conditions": "favorable",
                        },
                    },
                    "expected_outputs": {
                        "response": {
                            "response": "# Financial Document Analysis\n\n## Executive Summary\nThis Q4 2024 financial report demonstrates strong performance with significant revenue growth and improved profitability metrics...\n\n## Key Financial Highlights\n- **Revenue Growth**: 23% YoY increase to $156M\n- **Profitability**: EBITDA margin expansion to 18.5%\n- **Visual Analysis**: Charts show consistent upward trajectory...",
                            "confidence_score": 0.92,
                            "token_usage": {
                                "input_tokens": 1850,
                                "output_tokens": 2240,
                                "total_tokens": 4090,
                                "cost_usd": 0.0891,
                            },
                            "processing_time": 4.7,
                            "model_version": "claude-sonnet-4-20250514",
                        },
                        "structured_data": {
                            "executive_summary": "Strong Q4 2024 performance with 23% revenue growth and improved margins indicating healthy business trajectory",
                            "key_metrics": {
                                "revenue": "$156M",
                                "revenue_growth": "23% YoY",
                                "ebitda_margin": "18.5%",
                                "margin_improvement": "4.3 percentage points",
                            },
                            "visual_insights": [
                                "Revenue chart shows consistent quarterly growth with Q4 showing acceleration",
                                "Balance sheet indicates strong cash position and manageable debt levels",
                            ],
                            "investment_recommendation": "Positive",
                            "risk_factors": [
                                "Market saturation concerns in core segments",
                                "Increased competition from established players",
                            ],
                            "strengths": [
                                "Strong revenue growth trajectory",
                                "Improving operational efficiency",
                                "Healthy cash flow generation",
                            ],
                        },
                    },
                },
                {
                    "name": "Complex Problem Solving with Reasoning",
                    "description": "Solve complex multi-step problems with detailed reasoning and step-by-step analysis",
                    "configurations": {
                        "anthropic_api_key": "sk-ant-your_api_key_here",
                        "model": "claude-sonnet-4-20250514",
                        "system_prompt": "You are an expert problem solver and strategic analyst. For complex problems:\n1. Break down the problem into components\n2. Analyze each component systematically\n3. Consider multiple solution approaches\n4. Evaluate trade-offs and implications\n5. Provide clear, actionable recommendations\n6. Show your reasoning process step by step",
                        "user_prompt": "**Problem Context:** {{problem_context}}\n\n**Challenge:** {{problem_description}}\n\n**Constraints:** {{constraints}}\n\n**Success Criteria:** {{success_criteria}}\n\n**Additional Information:** {{additional_info}}\n\nPlease provide:\n1. Problem analysis and breakdown\n2. Multiple solution approaches\n3. Recommended solution with reasoning\n4. Implementation roadmap\n5. Risk assessment and mitigation strategies",
                        "max_tokens": 8192,
                        "temperature": 0.5,
                        "thinking_mode": True,
                        "response_format": "structured",
                        "output_processing": {"validate_output": True},
                    },
                    "input_example": {
                        "user_input": {
                            "problem_context": "Mid-size SaaS company experiencing rapid growth but facing scaling challenges",
                            "problem_description": "Our customer support team is overwhelmed with 300% increase in ticket volume over 6 months. Response times have increased from 2 hours to 24+ hours, causing customer satisfaction to drop from 4.8/5 to 3.2/5. We need to scale support operations while maintaining quality and managing costs.",
                            "constraints": [
                                "Limited budget: $200K for next 6 months",
                                "Cannot hire more than 5 additional staff",
                                "Must maintain current service quality standards",
                                "Existing team is already at capacity",
                                "Implementation must be completed within 90 days",
                            ],
                            "success_criteria": [
                                "Reduce average response time to under 4 hours",
                                "Improve customer satisfaction to 4.5+/5",
                                "Handle ticket volume growth sustainably",
                                "Keep cost per ticket under $25",
                            ],
                            "additional_info": "Current tools: Zendesk, Slack. Team size: 12 agents. Ticket types: 40% technical, 35% billing, 25% general inquiries.",
                        },
                        "context": {
                            "industry": "SaaS",
                            "company_stage": "growth",
                            "urgency": "high",
                        },
                    },
                    "expected_outputs": {
                        "response": {
                            "response": "# Customer Support Scaling Strategy\n\n## Problem Analysis\n\n### Core Issues Identified\n1. **Volume Growth**: 300% increase in tickets overwhelming current capacity\n2. **Response Time Degradation**: 24+ hours vs. 2-hour target\n3. **Quality Impact**: Customer satisfaction dropped significantly\n4. **Resource Constraints**: Limited budget and hiring capacity\n\n## Recommended Multi-Pronged Solution\n\n### Phase 1: Immediate Optimization (30 days)\n**AI-Powered Triage and Automation**\n- Implement intelligent ticket routing\n- Deploy chatbot for common inquiries\n- Automate billing-related responses\n\n### Phase 2: Strategic Enhancement (60 days)\n**Hybrid Human-AI Support Model**\n- Train AI assistants for technical support\n- Implement self-service knowledge base\n- Deploy sentiment analysis for prioritization\n\n### Phase 3: Sustainable Scaling (90 days)\n**Process Optimization and Team Expansion**\n- Hire 3 specialized agents for complex issues\n- Establish tier-based support structure\n- Implement performance monitoring dashboard...",
                            "thinking_process": "Let me break down this customer support scaling challenge systematically:\n\n1. Problem Analysis:\n   - 300% ticket volume increase is significant\n   - 2 hours → 24+ hours response time is critical\n   - Customer satisfaction drop from 4.8 to 3.2 is severe\n   - Budget constraint of $200K is moderate\n   - 90-day timeline is aggressive but achievable\n\n2. Root Cause Analysis:\n   - Primary: Volume exceeded capacity\n   - Secondary: No automation or intelligent routing\n   - Tertiary: Inefficient ticket categorization\n\n3. Solution Approaches:\n   - Approach A: Pure automation (high tech, low cost)\n   - Approach B: Staff expansion (low tech, high cost)\n   - Approach C: Hybrid model (balanced approach) ← Recommended\n\n4. Evaluation Criteria:\n   - Cost effectiveness within $200K budget\n   - Scalability for future growth\n   - Implementation feasibility in 90 days\n   - Impact on customer satisfaction...",
                            "confidence_score": 0.88,
                            "token_usage": {
                                "input_tokens": 520,
                                "output_tokens": 3200,
                                "total_tokens": 3720,
                                "cost_usd": 0.0712,
                            },
                            "processing_time": 5.1,
                            "model_version": "claude-sonnet-4-20250514",
                        },
                        "structured_data": {
                            "problem_breakdown": [
                                "Volume management challenge",
                                "Response time performance gap",
                                "Customer satisfaction decline",
                                "Resource optimization need",
                            ],
                            "solution_approaches": [
                                {
                                    "name": "AI-First Automation",
                                    "pros": ["Low cost", "High scalability", "24/7 availability"],
                                    "cons": ["Complex implementation", "Customer acceptance risk"],
                                    "cost_estimate": "$80K",
                                    "timeline": "60 days",
                                },
                                {
                                    "name": "Hybrid Human-AI Model",
                                    "pros": ["Balanced approach", "Quality maintained", "Scalable"],
                                    "cons": ["Moderate complexity"],
                                    "cost_estimate": "$150K",
                                    "timeline": "90 days",
                                    "recommended": True,
                                },
                            ],
                            "implementation_roadmap": [
                                {
                                    "phase": "Phase 1 - Quick Wins",
                                    "duration": "30 days",
                                    "activities": [
                                        "Deploy AI triage",
                                        "Implement chatbot",
                                        "Optimize workflows",
                                    ],
                                    "expected_impact": "30% ticket reduction",
                                },
                                {
                                    "phase": "Phase 2 - Strategic Enhancement",
                                    "duration": "30 days",
                                    "activities": [
                                        "AI assistant training",
                                        "Knowledge base expansion",
                                        "Sentiment analysis",
                                    ],
                                    "expected_impact": "50% response time improvement",
                                },
                                {
                                    "phase": "Phase 3 - Scaling",
                                    "duration": "30 days",
                                    "activities": [
                                        "Specialized hiring",
                                        "Tiered support",
                                        "Performance monitoring",
                                    ],
                                    "expected_impact": "Target metrics achievement",
                                },
                            ],
                            "risk_assessment": [
                                {
                                    "risk": "AI implementation complexity",
                                    "probability": "Medium",
                                    "impact": "High",
                                    "mitigation": "Phased rollout with human oversight",
                                },
                                {
                                    "risk": "Customer adoption resistance",
                                    "probability": "Low",
                                    "impact": "Medium",
                                    "mitigation": "Transparent communication and opt-out options",
                                },
                            ],
                        },
                    },
                },
            ],
        )


# Export the specification instance
ANTHROPIC_CLAUDE_SPEC = AnthropicClaudeSpec()
