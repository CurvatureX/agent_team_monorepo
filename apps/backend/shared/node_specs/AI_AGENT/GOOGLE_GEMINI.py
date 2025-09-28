"""
GOOGLE_GEMINI AI Agent Node Specification

Google Gemini AI agent node for performing advanced AI operations including
multi-modal processing, code generation, reasoning, analysis, and creative tasks.
"""

from typing import Any, Dict, List

from ...models.node_enums import AIAgentSubtype, GoogleGeminiModel, NodeType
from ..base import COMMON_CONFIGS, BaseNodeSpec, create_port


class GoogleGeminiSpec(BaseNodeSpec):
    """Google Gemini AI agent specification for advanced multi-modal AI processing."""

    def __init__(self):
        super().__init__(
            type=NodeType.AI_AGENT,
            subtype=AIAgentSubtype.GOOGLE_GEMINI,
            name="Google_Gemini",
            description="Google Gemini AI agent for advanced multi-modal processing, reasoning, code generation, and creative tasks",
            # Configuration parameters
            configurations={
                "google_api_key": {
                    "type": "string",
                    "default": "",
                    "description": "Google AI API密钥",
                    "required": True,
                    "sensitive": True,
                },
                "model": {
                    "type": "string",
                    "default": GoogleGeminiModel.GEMINI_2_5_FLASH.value,
                    "description": "Gemini模型版本",
                    "required": True,
                    "options": [model.value for model in GoogleGeminiModel],
                },
                "system_instruction": {
                    "type": "string",
                    "default": "",
                    "description": "系统指令",
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
                "generation_config": {
                    "type": "object",
                    "default": {
                        "max_output_tokens": 8192,
                        "temperature": 0.7,
                        "top_p": 0.95,
                        "top_k": 40,
                        "candidate_count": 1,
                        "stop_sequences": [],
                    },
                    "description": "生成配置",
                    "required": False,
                },
                "safety_settings": {
                    "type": "object",
                    "default": {
                        "harassment": "BLOCK_MEDIUM_AND_ABOVE",
                        "hate_speech": "BLOCK_MEDIUM_AND_ABOVE",
                        "sexually_explicit": "BLOCK_MEDIUM_AND_ABOVE",
                        "dangerous_content": "BLOCK_MEDIUM_AND_ABOVE",
                    },
                    "description": "安全配置",
                    "required": False,
                },
                "multimodal_config": {
                    "type": "object",
                    "default": {
                        "enable_vision": True,
                        "enable_audio": False,
                        "enable_video": False,
                        "max_images": 16,
                        "max_audio_duration": 300,
                        "max_video_duration": 60,
                        "supported_image_formats": ["jpeg", "png", "gif", "webp"],
                        "supported_audio_formats": ["wav", "mp3", "aac", "ogg"],
                        "supported_video_formats": ["mp4", "avi", "mov", "webm"],
                    },
                    "description": "多模态配置",
                    "required": False,
                },
                "function_calling": {
                    "type": "object",
                    "default": {"enabled": False, "functions": [], "function_calling_mode": "AUTO"},
                    "description": "函数调用配置",
                    "required": False,
                },
                "code_execution": {
                    "type": "object",
                    "default": {
                        "enabled": False,
                        "supported_languages": ["python", "javascript", "sql"],
                        "timeout_seconds": 30,
                        "memory_limit_mb": 256,
                    },
                    "description": "代码执行配置",
                    "required": False,
                },
                "thinking_config": {
                    "type": "object",
                    "default": {
                        "enable_thinking": False,
                        "thinking_budget": 32768,
                        "show_thinking_process": False,
                    },
                    "description": "思维配置（Gemini 2.5 Flash特性）",
                    "required": False,
                },
                "response_format": {
                    "type": "string",
                    "default": "text",
                    "description": "响应格式",
                    "required": False,
                    "options": ["text", "json", "structured", "markdown", "code"],
                },
                "context_caching": {
                    "type": "object",
                    "default": {
                        "enabled": False,
                        "cache_ttl": 3600,
                        "context_size_threshold": 32768,
                    },
                    "description": "上下文缓存配置",
                    "required": False,
                },
                "output_processing": {
                    "type": "object",
                    "default": {
                        "enable_streaming": False,
                        "parse_json": False,
                        "extract_code": False,
                        "validate_schema": False,
                        "output_schema": {},
                    },
                    "description": "输出处理配置",
                    "required": False,
                },
                "performance_config": {
                    "type": "object",
                    "default": {
                        "timeout_seconds": 120,
                        "retry_attempts": 3,
                        "retry_delay": 2.0,
                        "exponential_backoff": True,
                        "rate_limit_handling": True,
                    },
                    "description": "性能配置",
                    "required": False,
                },
                "cost_optimization": {
                    "type": "object",
                    "default": {
                        "use_cached_content": True,
                        "compress_images": True,
                        "optimize_prompts": False,
                        "batch_requests": False,
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
                "audio_files": [],
                "video_files": [],
                "documents": [],
            },
            default_output_params={
                "response": "",
                "thinking_process": "",
                "confidence_score": 0.0,
                "token_usage": {},
                "processing_time": 0.0,
                "function_calls": [],
                "code_results": {},
                "extracted_data": {},
                "safety_ratings": {},
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
                    port_id="media",
                    name="media",
                    data_type="dict",
                    description="Multi-modal media inputs (images, audio, video)",
                    required=False,
                    max_connections=1,
                ),
            ],
            output_ports=[
                create_port(
                    port_id="response",
                    name="response",
                    data_type="dict",
                    description="Gemini's response and metadata",
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
                    port_id="code_execution",
                    name="code_execution",
                    data_type="dict",
                    description="Code execution results and outputs",
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
            tags=[
                "ai-agent",
                "google",
                "gemini",
                "llm",
                "multimodal",
                "reasoning",
                "code-generation",
            ],
            # Examples
            examples=[
                {
                    "name": "Multi-Modal Content Analysis with Video",
                    "description": "Analyze video content with audio and visual elements for comprehensive insights",
                    "configurations": {
                        "google_api_key": "AIzaSyYour_API_Key_Here",
                        "model": "gemini-2.5-pro",
                        "system_instruction": "You are an expert multimedia content analyst. Analyze video content comprehensively, focusing on:\n1. Visual elements and scenes\n2. Audio content and speech\n3. Narrative structure\n4. Key themes and messages\n5. Technical quality assessment\n6. Audience engagement factors",
                        "user_prompt": "Analyze this video content:\n\n**Video Type:** {{video_type}}\n**Duration:** {{duration}}\n**Purpose:** {{analysis_purpose}}\n\nProvide comprehensive analysis including:\n1. Scene-by-scene breakdown\n2. Audio analysis (speech, music, effects)\n3. Visual quality assessment\n4. Content themes and messaging\n5. Engagement recommendations\n6. Technical improvements suggestions",
                        "generation_config": {
                            "max_output_tokens": 16384,
                            "temperature": 0.4,
                            "top_p": 0.9,
                        },
                        "multimodal_config": {
                            "enable_vision": True,
                            "enable_audio": True,
                            "enable_video": True,
                            "max_video_duration": 300,
                            "supported_video_formats": ["mp4", "mov", "webm"],
                        },
                        "thinking_config": {
                            "enable_thinking": True,
                            "thinking_budget": 65536,
                            "show_thinking_process": True,
                        },
                    },
                    "input_example": {
                        "user_input": {
                            "video_type": "Product Demo",
                            "duration": "3:24",
                            "analysis_purpose": "Marketing effectiveness assessment",
                        },
                        "media": {
                            "video_files": [
                                {
                                    "data": "base64_encoded_video_data...",
                                    "mime_type": "video/mp4",
                                    "filename": "product_demo_v2.mp4",
                                }
                            ]
                        },
                        "context": {
                            "product_name": "SmartHome Hub",
                            "target_audience": "tech-savvy homeowners",
                            "marketing_goals": ["awareness", "conversion"],
                        },
                    },
                    "expected_outputs": {
                        "response": {
                            "response": "# Video Content Analysis: SmartHome Hub Product Demo\n\n## Executive Summary\nThis 3:24 product demonstration effectively showcases the SmartHome Hub's key features with strong visual presentation and clear narration...\n\n## Scene-by-Scene Analysis\n\n### Opening Scene (0:00-0:15)\n- **Visual**: Clean, modern home setting with natural lighting\n- **Audio**: Upbeat background music with professional voiceover\n- **Message**: Establishes aspirational home environment\n- **Effectiveness**: Strong hook with clear value proposition\n\n### Feature Demonstration (0:15-2:30)\n- **Visual**: Close-up shots of device interaction, smooth transitions\n- **Audio**: Clear narration explaining each feature\n- **Technical Quality**: 4K resolution, stable camera work\n- **Engagement**: Interactive elements maintain viewer interest\n\n### Call-to-Action (2:30-3:24)\n- **Visual**: Product packaging and purchase information\n- **Audio**: Compelling final message with urgency\n- **Conversion Elements**: Clear pricing and availability\n\n## Audio Analysis\n- **Narration Quality**: Professional, clear, appropriate pace\n- **Background Music**: Complements content without distraction\n- **Sound Effects**: Subtle device interaction sounds enhance realism\n- **Overall Audio Score**: 8.5/10\n\n## Recommendations\n1. **Extend Feature Demos**: Show more real-world scenarios\n2. **Add Customer Testimonials**: Include brief user experiences\n3. **Improve Call-to-Action**: Make purchase button more prominent\n4. **Social Proof**: Display user ratings or reviews",
                            "thinking_process": "Let me analyze this product demo video systematically:\n\n1. First, I'll examine the visual composition:\n   - The opening establishes a premium home environment\n   - Lighting is professional and creates aspirational mood\n   - Camera work is stable with smooth transitions\n   - Product shots are well-framed and clear\n\n2. Audio assessment:\n   - Voiceover is professional and engaging\n   - Background music enhances without overwhelming\n   - Sound design supports the premium positioning\n   - Audio levels are well-balanced throughout\n\n3. Content structure analysis:\n   - Hook: Strong opening with clear value prop\n   - Body: Feature demonstrations are logical\n   - Close: Call-to-action could be stronger\n\n4. Marketing effectiveness:\n   - Target audience alignment: Good for tech-savvy users\n   - Value proposition clarity: Very clear\n   - Conversion elements: Present but could be enhanced\n\n5. Technical quality:\n   - Video resolution: High quality\n   - Color grading: Consistent and appealing\n   - Motion graphics: Professional integration",
                            "confidence_score": 0.91,
                            "token_usage": {
                                "input_tokens": 2450,
                                "output_tokens": 3100,
                                "total_tokens": 5550,
                                "cost_usd": 0.0831,
                            },
                            "processing_time": 8.2,
                            "model_version": "gemini-2.5-pro",
                        },
                        "structured_data": {
                            "overall_rating": 8.2,
                            "scene_breakdown": [
                                {
                                    "timestamp": "0:00-0:15",
                                    "type": "opening",
                                    "visual_quality": 9,
                                    "audio_quality": 8,
                                    "effectiveness": 8.5,
                                    "key_elements": ["aspirational_setting", "clear_value_prop"],
                                },
                                {
                                    "timestamp": "0:15-2:30",
                                    "type": "demonstration",
                                    "visual_quality": 8.5,
                                    "audio_quality": 9,
                                    "effectiveness": 8,
                                    "key_elements": [
                                        "feature_showcase",
                                        "clear_narration",
                                        "smooth_transitions",
                                    ],
                                },
                            ],
                            "strengths": [
                                "High production quality",
                                "Clear feature demonstration",
                                "Professional narration",
                                "Aspirational positioning",
                            ],
                            "improvement_areas": [
                                "Extend real-world scenarios",
                                "Add social proof elements",
                                "Strengthen call-to-action",
                                "Include customer testimonials",
                            ],
                            "marketing_effectiveness": {
                                "awareness_factor": 8.5,
                                "conversion_potential": 7.0,
                                "brand_alignment": 9.0,
                                "target_audience_fit": 8.5,
                            },
                        },
                    },
                },
                {
                    "name": "Advanced Code Generation and Execution",
                    "description": "Generate, analyze, and execute code with real-time testing and optimization",
                    "configurations": {
                        "google_api_key": "AIzaSyYour_API_Key_Here",
                        "model": "gemini-2.5-pro",
                        "system_instruction": "You are an expert software engineer specializing in code generation, optimization, and testing. When generating code:\n1. Write clean, efficient, and well-documented code\n2. Include comprehensive error handling\n3. Add unit tests when appropriate\n4. Consider performance implications\n5. Follow best practices for the target language\n6. Explain your design decisions",
                        "user_prompt": "**Task:** {{coding_task}}\n**Language:** {{programming_language}}\n**Requirements:** {{requirements}}\n**Constraints:** {{constraints}}\n\nPlease:\n1. Analyze the requirements\n2. Design the solution architecture\n3. Generate the complete code implementation\n4. Create unit tests\n5. Execute and validate the code\n6. Provide optimization suggestions",
                        "generation_config": {
                            "max_output_tokens": 16384,
                            "temperature": 0.2,
                            "top_p": 0.8,
                        },
                        "code_execution": {
                            "enabled": True,
                            "supported_languages": ["python", "javascript", "sql"],
                            "timeout_seconds": 45,
                            "memory_limit_mb": 512,
                        },
                        "function_calling": {
                            "enabled": True,
                            "functions": [
                                {
                                    "name": "execute_code",
                                    "description": "Execute code and return results",
                                    "parameters": {
                                        "type": "object",
                                        "properties": {
                                            "language": {"type": "string"},
                                            "code": {"type": "string"},
                                        },
                                    },
                                }
                            ],
                        },
                    },
                    "input_example": {
                        "user_input": {
                            "coding_task": "Create a rate limiter class that can handle multiple rate limiting strategies",
                            "programming_language": "Python",
                            "requirements": [
                                "Support token bucket and sliding window algorithms",
                                "Thread-safe implementation",
                                "Configurable rate limits per user/API key",
                                "Redis backend for distributed systems",
                                "Comprehensive logging and metrics",
                            ],
                            "constraints": [
                                "Must be production-ready",
                                "Include comprehensive error handling",
                                "Memory efficient for high throughput",
                                "Support both sync and async operations",
                            ],
                        },
                        "context": {
                            "use_case": "API gateway rate limiting",
                            "expected_qps": 10000,
                            "deployment": "distributed",
                        },
                    },
                    "expected_outputs": {
                        "response": {
                            "response": "# Advanced Rate Limiter Implementation\n\n## Architecture Overview\nI'll create a flexible rate limiter supporting multiple strategies with Redis backend for distributed systems.\n\n## Implementation\n\n### Core Rate Limiter Class\n```python\nimport asyncio\nimport time\nimport threading\nfrom abc import ABC, abstractmethod\nfrom typing import Dict, Optional, Union\nfrom dataclasses import dataclass\nimport redis\nimport json\nimport logging\n\n@dataclass\nclass RateLimitConfig:\n    requests_per_window: int\n    window_size_seconds: int\n    strategy: str  # 'token_bucket' or 'sliding_window'\n    burst_allowance: Optional[int] = None\n\nclass RateLimitStrategy(ABC):\n    @abstractmethod\n    def is_allowed(self, key: str, config: RateLimitConfig) -> tuple[bool, dict]:\n        pass\n\nclass TokenBucketStrategy(RateLimitStrategy):\n    def __init__(self, redis_client):\n        self.redis = redis_client\n        self.logger = logging.getLogger(__name__)\n    \n    def is_allowed(self, key: str, config: RateLimitConfig) -> tuple[bool, dict]:\n        \"\"\"Token bucket algorithm with Redis backend\"\"\"\n        bucket_key = f\"bucket:{key}\"\n        current_time = time.time()\n        \n        with self.redis.pipeline() as pipe:\n            try:\n                pipe.multi()\n                bucket_data = pipe.hmget(bucket_key, 'tokens', 'last_refill')\n                \n                if bucket_data[0] is None:\n                    # Initialize bucket\n                    tokens = config.requests_per_window\n                    last_refill = current_time\n                else:\n                    tokens = float(bucket_data[0])\n                    last_refill = float(bucket_data[1])\n                \n                # Calculate tokens to add based on time elapsed\n                time_elapsed = current_time - last_refill\n                tokens_to_add = time_elapsed * (config.requests_per_window / config.window_size_seconds)\n                tokens = min(config.requests_per_window, tokens + tokens_to_add)\n                \n                if tokens >= 1:\n                    # Allow request and consume token\n                    tokens -= 1\n                    pipe.hmset(bucket_key, {\n                        'tokens': tokens,\n                        'last_refill': current_time\n                    })\n                    pipe.expire(bucket_key, config.window_size_seconds * 2)\n                    pipe.execute()\n                    \n                    return True, {\n                        'remaining': int(tokens),\n                        'reset_time': current_time + (config.requests_per_window - tokens) * (config.window_size_seconds / config.requests_per_window)\n                    }\n                else:\n                    # Rate limit exceeded\n                    return False, {\n                        'remaining': 0,\n                        'reset_time': current_time + (config.window_size_seconds / config.requests_per_window)\n                    }\n                    \n            except redis.RedisError as e:\n                self.logger.error(f\"Redis error in token bucket: {e}\")\n                # Fail open in case of Redis issues\n                return True, {'remaining': -1, 'reset_time': current_time + 60}\n\nclass DistributedRateLimiter:\n    def __init__(self, redis_url: str = \"redis://localhost:6379\"):\n        self.redis = redis.from_url(redis_url, decode_responses=True)\n        self.strategies = {\n            'token_bucket': TokenBucketStrategy(self.redis),\n            'sliding_window': SlidingWindowStrategy(self.redis)\n        }\n        self.configs: Dict[str, RateLimitConfig] = {}\n        self.lock = threading.RLock()\n        self.logger = logging.getLogger(__name__)\n    \n    def configure(self, identifier: str, config: RateLimitConfig):\n        \"\"\"Configure rate limiting for a specific identifier\"\"\"\n        with self.lock:\n            self.configs[identifier] = config\n            self.logger.info(f\"Configured rate limit for {identifier}: {config}\")\n    \n    def is_allowed(self, identifier: str, user_key: Optional[str] = None) -> tuple[bool, dict]:\n        \"\"\"Check if request is allowed\"\"\"\n        if identifier not in self.configs:\n            self.logger.warning(f\"No configuration found for {identifier}, allowing request\")\n            return True, {'remaining': -1}\n        \n        config = self.configs[identifier]\n        cache_key = f\"{identifier}:{user_key or 'default'}\"\n        strategy = self.strategies.get(config.strategy)\n        \n        if not strategy:\n            self.logger.error(f\"Unknown strategy: {config.strategy}\")\n            return True, {'remaining': -1}\n        \n        try:\n            return strategy.is_allowed(cache_key, config)\n        except Exception as e:\n            self.logger.error(f\"Rate limiter error: {e}\")\n            return True, {'remaining': -1}  # Fail open\n    \n    async def is_allowed_async(self, identifier: str, user_key: Optional[str] = None) -> tuple[bool, dict]:\n        \"\"\"Async version of is_allowed\"\"\"\n        # Run in thread pool to avoid blocking\n        loop = asyncio.get_event_loop()\n        return await loop.run_in_executor(None, self.is_allowed, identifier, user_key)\n```\n\n### Unit Tests\n```python\nimport unittest\nimport time\nfrom unittest.mock import patch, MagicMock\n\nclass TestRateLimiter(unittest.TestCase):\n    def setUp(self):\n        self.mock_redis = MagicMock()\n        self.rate_limiter = DistributedRateLimiter()\n        self.rate_limiter.redis = self.mock_redis\n    \n    def test_token_bucket_allows_within_limit(self):\n        config = RateLimitConfig(\n            requests_per_window=10,\n            window_size_seconds=60,\n            strategy='token_bucket'\n        )\n        self.rate_limiter.configure('test_api', config)\n        \n        # Mock Redis responses\n        self.mock_redis.pipeline.return_value.__enter__.return_value.hmget.return_value = [None, None]\n        \n        allowed, info = self.rate_limiter.is_allowed('test_api', 'user123')\n        self.assertTrue(allowed)\n        self.assertIn('remaining', info)\n    \n    def test_rate_limit_exceeded(self):\n        config = RateLimitConfig(\n            requests_per_window=1,\n            window_size_seconds=60,\n            strategy='token_bucket'\n        )\n        self.rate_limiter.configure('test_api', config)\n        \n        # Mock Redis to simulate no tokens left\n        self.mock_redis.pipeline.return_value.__enter__.return_value.hmget.return_value = ['0', str(time.time())]\n        \n        allowed, info = self.rate_limiter.is_allowed('test_api', 'user123')\n        self.assertFalse(allowed)\n        self.assertEqual(info['remaining'], 0)\n```\n\n## Optimization Recommendations\n1. **Connection Pooling**: Use Redis connection pooling for better performance\n2. **Lua Scripts**: Move complex Redis operations to Lua scripts for atomicity\n3. **Monitoring**: Add comprehensive metrics and alerting\n4. **Circuit Breaker**: Implement circuit breaker pattern for Redis failures\n5. **Local Caching**: Add local cache for frequently accessed rate limit data",
                            "confidence_score": 0.94,
                            "token_usage": {
                                "input_tokens": 680,
                                "output_tokens": 4200,
                                "total_tokens": 4880,
                                "cost_usd": 0.0732,
                            },
                            "processing_time": 6.8,
                            "model_version": "gemini-2.5-pro",
                        },
                        "code_execution": {
                            "execution_successful": True,
                            "output": "Rate limiter test execution completed successfully.\nAll unit tests passed: 2/2\nPerformance test: Handled 1000 requests in 0.245 seconds\nMemory usage: 12.4 MB peak",
                            "execution_time": 1.8,
                            "memory_used_mb": 12.4,
                            "test_results": {
                                "tests_run": 2,
                                "tests_passed": 2,
                                "tests_failed": 0,
                                "coverage_percentage": 87.5,
                            },
                        },
                        "structured_data": {
                            "implementation_features": [
                                "Token bucket algorithm",
                                "Thread-safe operations",
                                "Redis distributed backend",
                                "Comprehensive error handling",
                                "Async/sync support",
                                "Configurable rate limits",
                                "Fail-open strategy",
                            ],
                            "performance_metrics": {
                                "requests_per_second": 4081,
                                "memory_efficiency": "high",
                                "latency_p95": "2.3ms",
                                "redis_operations_per_request": 1.2,
                            },
                            "code_quality": {
                                "test_coverage": 87.5,
                                "complexity_score": "medium",
                                "documentation": "comprehensive",
                                "error_handling": "robust",
                            },
                        },
                    },
                },
                {
                    "name": "Creative Content Generation with Style Transfer",
                    "description": "Generate creative content with specific style, tone, and format requirements",
                    "configurations": {
                        "google_api_key": "AIzaSyYour_API_Key_Here",
                        "model": "gemini-2.5-flash",
                        "system_instruction": "You are a versatile creative writer and content strategist. Create engaging content that:\n1. Matches the specified tone and style perfectly\n2. Resonates with the target audience\n3. Achieves the stated objectives\n4. Incorporates SEO best practices when applicable\n5. Maintains brand consistency\n6. Uses compelling storytelling techniques",
                        "user_prompt": "Create {{content_type}} with the following specifications:\n\n**Topic:** {{topic}}\n**Target Audience:** {{target_audience}}\n**Tone:** {{tone}}\n**Style:** {{style}}\n**Length:** {{length}}\n**Objectives:** {{objectives}}\n**Key Messages:** {{key_messages}}\n**Brand Guidelines:** {{brand_guidelines}}\n\nAdditional Requirements:\n{{additional_requirements}}\n\nPlease create compelling content that achieves all objectives while maintaining the specified tone and style.",
                        "generation_config": {
                            "max_output_tokens": 8192,
                            "temperature": 0.8,
                            "top_p": 0.95,
                            "top_k": 50,
                        },
                        "thinking_config": {
                            "enable_thinking": True,
                            "thinking_budget": 16384,
                            "show_thinking_process": False,
                        },
                        "response_format": "structured",
                    },
                    "input_example": {
                        "user_input": {
                            "content_type": "Blog post",
                            "topic": "Remote work productivity tips for software developers",
                            "target_audience": "Software developers working remotely, aged 25-40, tech-savvy",
                            "tone": "Conversational yet authoritative, friendly but professional",
                            "style": "Practical guide with actionable insights, personal anecdotes, and data-backed recommendations",
                            "length": "2000-2500 words",
                            "objectives": [
                                "Increase blog engagement",
                                "Position as thought leader",
                                "Drive newsletter signups",
                            ],
                            "key_messages": [
                                "Remote work requires intentional productivity strategies",
                                "Work-life balance is crucial for long-term success",
                                "Technology tools can enhance but not replace good habits",
                            ],
                            "brand_guidelines": "Tech-forward, developer-focused, evidence-based, inclusive",
                            "additional_requirements": "Include actionable tips, relevant statistics, and call-to-action for newsletter signup",
                        },
                        "context": {
                            "publication": "Developer productivity blog",
                            "seo_keywords": [
                                "remote work",
                                "developer productivity",
                                "work from home",
                            ],
                            "target_engagement": "high social shares, comments",
                        },
                    },
                    "expected_outputs": {
                        "response": {
                            "response": "# The Remote Developer's Guide to Peak Productivity: 12 Game-Changing Strategies That Actually Work\n\n*Published on [Date] | 8 min read*\n\n## Introduction\n\nThree years ago, I thought remote work meant endless freedom and unlimited productivity. I was wrong on both counts.\n\nAfter struggling through my first six months of remote development work—complete with 14-hour \"workdays\" that yielded maybe 4 hours of actual coding—I realized something crucial: remote work doesn't automatically make you more productive. In fact, without the right strategies, it can completely derail your career.\n\nToday, I'm sharing 12 battle-tested productivity strategies that transformed my remote work experience from chaotic to systematic, from overwhelming to empowering. These aren't theoretical productivity hacks—they're practical techniques I've refined through trial, error, and input from hundreds of remote developers in our community.\n\n*According to Stack Overflow's 2024 Developer Survey, 67% of developers now work remotely at least part-time, but only 34% report feeling \"highly productive\" in their remote setup. Let's change that.*\n\n## The Foundation: Environment and Mindset\n\n### 1. Design Your Developer Sanctuary\n\nYour workspace isn't just where you code—it's where your productivity lives or dies.\n\n**The Setup That Works:**\n- **Dual monitors minimum** (triple if budget allows): 73% of developers report increased productivity with multiple screens\n- **Ergonomic chair and desk**: Your back will thank you during those debugging marathons\n- **Dedicated workspace**: Even if it's just a corner, make it exclusively yours\n- **Quality lighting**: Natural light when possible, blue light filters after sunset\n\n**Pro tip:** Create a \"context switch\" ritual. Mine involves making coffee, reviewing my daily goals, and playing the same 5-minute instrumental playlist. This signals to my brain that it's time to code.\n\n### 2. Master the Art of Deep Work Blocks\n\nConstant notifications are productivity cancer. Here's how to perform surgery:\n\n**The 90-Minute Rule:**\nBased on ultradian rhythms research, work in 90-minute focused blocks followed by 20-minute breaks. During these blocks:\n- Phone in another room (seriously)\n- All notifications off except critical alerts\n- Single-tasking only\n- One complex problem at a time\n\n**Implementation tip:** Use the Pomodoro Technique as training wheels, then graduate to longer focus blocks as your concentration muscle strengthens.\n\n## Communication and Collaboration\n\n### 3. Async Communication Mastery\n\nRemote work lives and dies by asynchronous communication. Master these principles:\n\n**The BRIEF Method:**\n- **B**ackground: Context in 1-2 sentences\n- **R**eason: Why this matters now\n- **I**nformation: Key details, no fluff\n- **E**nd State: What success looks like\n- **F**ollow-up: Next steps and timeline\n\n**Example transformation:**\n❌ \"Hey, can we talk about the API thing?\"\n✅ \"**Background:** User authentication API returning 500 errors since deploy. **Reason:** 15% of logins failing, blocking user onboarding. **Information:** Error occurs in JWT validation middleware, logs show memory spike. **End State:** Stable authentication with <1% error rate. **Follow-up:** Can you review the middleware changes by EOD? I'll handle the rollback plan.\"\n\n### 4. Meeting Hygiene (Yes, It's a Thing)\n\n**The 25% Rule:** Cancel 25% of your recurring meetings. Seriously. Right now.\n\nFor meetings you keep:\n- **Agenda sent 24 hours prior** (no agenda = no meeting)\n- **Start with the end in mind**: What decision needs to be made?\n- **Action items with owners and dates**\n- **Default to 25 or 50 minutes** (not 30/60) for transition time\n\n## Technical Productivity\n\n### 5. Development Environment Optimization\n\nYour dev environment should be a well-oiled machine:\n\n**Essential Optimizations:**\n```bash\n# Terminal productivity\nalias gst='git status'\nalias gco='git checkout'\nalias gp='git push origin HEAD'\n\n# Fast directory navigation\nfunction proj() {\n  cd ~/projects/$1\n}\n\n# Quick server startup\nfunction dev() {\n  npm install && npm run dev\n}\n```\n\n**IDE Power-ups:**\n- Custom code snippets for common patterns\n- Project-specific settings synced across devices\n- Keyboard shortcuts for frequent actions (aim for 80% keyboard, 20% mouse)\n\n### 6. The Power of Automation\n\nAutomate ruthlessly. If you do it more than twice, script it.\n\n**High-Impact Automations:**\n- **Pre-commit hooks** for code formatting and linting\n- **Automated testing** in CI/CD pipeline\n- **Environment setup scripts** for new team members\n- **Daily standup templates** with yesterday's commits auto-populated\n\n## Time and Energy Management\n\n### 7. Energy-Based Scheduling\n\nTime management is outdated. Energy management is everything.\n\n**Track your energy patterns for one week:**\n- When do you feel most mentally sharp?\n- When do you hit the afternoon crash?\n- What activities drain vs. energize you?\n\n**Then optimize:**\n- **High-energy times**: Complex problem-solving, architecture decisions\n- **Medium energy**: Code reviews, refactoring, testing\n- **Low energy**: Documentation, admin tasks, learning\n\n### 8. The Context Switching Tax\n\nResearch shows it takes an average of 23 minutes to fully refocus after an interruption. Here's how to minimize the damage:\n\n**Batching Strategy:**\n- **Code review block**: 10am-11am daily\n- **Communication block**: 2pm-3pm daily\n- **Learning block**: 4pm-5pm daily\n\n**Context preservation:** Before switching tasks, write a quick note about where you left off and what to do next. Future you will be grateful.\n\n## Health and Sustainability\n\n### 9. The Remote Work Fitness Stack\n\nSedentary work is literally killing us. Combat it systematically:\n\n**The 20-20-20 Rule Plus:**\nEvery 20 minutes, look at something 20 feet away for 20 seconds, AND do 20 bodyweight exercises.\n\n**Walking meetings:** Perfect for brainstorming and one-on-ones\n**Standing desk rotation:** 25 minutes sitting, 35 minutes standing\n**Exercise snacking:** 5-minute movement breaks every hour\n\n### 10. Boundary Setting That Actually Works\n\n**The Shutdown Ritual:**\n1. Review tomorrow's priorities (5 min)\n2. Close all work applications\n3. Write three work wins from today\n4. Physically close laptop/turn off monitor\n5. Say \"I'm done with work\" out loud\n\nSounds cheesy? Maybe. Does it work? Absolutely.\n\n## Advanced Strategies\n\n### 11. The Learning Loop\n\nRemote work can lead to skill stagnation without intentional learning:\n\n**The 1% Rule:** Dedicate 1% of your work week (2.4 hours) to learning:\n- **Monday:** Read one technical article\n- **Wednesday:** Watch one conference talk\n- **Friday:** Experiment with new tool/technique\n\n**Knowledge sharing:** Teach what you learn. Start an internal tech talk series or contribute to team documentation.\n\n### 12. Metrics That Matter\n\nTrack your productivity with data, not feelings:\n\n**Weekly Review Questions:**\n- How many deep work hours did I log?\n- What was my energy level distribution?\n- Which meetings added value vs. drained time?\n- What automated task saved me the most time?\n- Where did I get stuck, and why?\n\n**Tools I recommend:**\n- **RescueTime** for time tracking\n- **Toggl** for project time allocation\n- **Oura Ring** for sleep and recovery data\n- **GitHub Insights** for code contribution patterns\n\n## Putting It All Together\n\nStarting all 12 strategies simultaneously is a recipe for failure. Instead:\n\n**Week 1-2:** Focus on workspace setup and deep work blocks\n**Week 3-4:** Add communication protocols and meeting hygiene\n**Week 5-6:** Implement automation and energy-based scheduling\n**Week 7-8:** Establish health routines and boundaries\n**Week 9-12:** Add advanced strategies and refine your system\n\n## The Bottom Line\n\nRemote work productivity isn't about working more hours—it's about working more intentionally. The strategies above aren't just productivity tips; they're career-changing systems that will serve you whether you're building the next unicorn startup or contributing to open source projects.\n\nRemember: productivity is deeply personal. Take these strategies as starting points, not gospel. Experiment, measure, adapt.\n\nYour future, more productive self is counting on the systems you build today.\n\n---\n\n**Ready to level up your remote work game?** Join 12,000+ developers getting our weekly productivity newsletter with actionable insights, tool recommendations, and success stories from the remote dev community.\n\n[Subscribe to Developer Productivity Weekly →]\n\n*What's your biggest remote work productivity challenge? Share it in the comments below—I read and respond to every one.*\n\n---\n\n**About the Author:** [Bio and credentials]\n\n**Tags:** #RemoteWork #DeveloperProductivity #WorkFromHome #SoftwareDevelopment #Productivity",
                            "thinking_process": "[Hidden thinking process about content strategy, audience analysis, and structure planning]",
                            "confidence_score": 0.89,
                            "token_usage": {
                                "input_tokens": 425,
                                "output_tokens": 3600,
                                "total_tokens": 4025,
                                "cost_usd": 0.0604,
                            },
                            "processing_time": 4.2,
                            "model_version": "gemini-2.5-flash",
                        },
                        "structured_data": {
                            "content_analysis": {
                                "word_count": 2247,
                                "readability_score": 8.2,
                                "tone_match": 0.94,
                                "seo_optimization": 0.87,
                                "engagement_factors": [
                                    "personal anecdotes",
                                    "actionable tips",
                                    "data-backed insights",
                                    "clear structure",
                                    "compelling headlines",
                                ],
                            },
                            "key_features": [
                                "12 comprehensive strategies",
                                "Personal storytelling elements",
                                "Statistical backing",
                                "Code examples and practical tips",
                                "Progressive implementation plan",
                                "Strong call-to-action",
                                "SEO-optimized structure",
                            ],
                            "audience_alignment": {
                                "technical_depth": "appropriate",
                                "tone_consistency": 0.94,
                                "relevance_score": 0.91,
                                "actionability": 0.96,
                            },
                            "content_objectives": {
                                "engagement_potential": "high",
                                "thought_leadership": "established",
                                "newsletter_conversion": "optimized",
                                "shareability": "high",
                            },
                        },
                    },
                },
            ],
        )


# Export the specification instance
GOOGLE_GEMINI_SPEC = GoogleGeminiSpec()
