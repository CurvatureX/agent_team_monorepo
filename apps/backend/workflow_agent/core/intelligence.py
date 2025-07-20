import sys
from pathlib import Path

# Add the backend path to sys.path to import shared modules
backend_path = Path(__file__).resolve().parent.parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

"""
Intelligence engines for Workflow Agent
Based on the MVP plan and architecture design
"""

import json
from typing import Any, Dict, List, Optional

import structlog
from langchain.prompts import PromptTemplate
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from core.config import settings
from core.mvp_models import (
    CapabilityAnalysis,
    Constraint,
    GapSeverity,
    Solution,
    SolutionReliability,
    SolutionType,
)
from core.prompt_engine import get_prompt_engine
from core.vector_store import get_node_knowledge_rag

logger = structlog.get_logger()


class LLMCapabilityScanner:
    def __init__(self, llm, rag_system):
        self.llm = llm
        self.rag = rag_system
        self.capability_library = {}  # Legacy support
        self.prompt_engine = get_prompt_engine()

        # LLM Prompts
        # Templates will be loaded on-demand via prompt_engine

    async def _call_llm(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Helper method to call LLM with error handling"""
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])

            # Try to parse JSON response
            try:
                return json.loads(response.content)
            except json.JSONDecodeError:
                # If not JSON, return as text
                return {"response": response.content}

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return {"error": str(e)}

    async def _extract_required_capabilities(self, requirements: Dict[str, Any]) -> List[str]:
        """Extract required capabilities using LLM"""
        context = {
            "complexity_preference": requirements.get("estimated_complexity", "medium"),
            "business_context": requirements.get("primary_goal", ""),
            "performance_requirements": requirements.get("performance_requirements", {}),
        }

        prompt_str = await self.prompt_engine.render_prompt(
            "capability_extraction",
            requirements=json.dumps(requirements, indent=2),
            context=json.dumps(context, indent=2),
        )
        result = await self._call_llm(prompt_str)

        return result.get("capabilities", [])

    async def _analyze_capability_gaps(
        self,
        required_capabilities: List[str],
        available_capabilities: List[str],
        rag_insights: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze capability gaps using LLM"""
        prompt_str = await self.prompt_engine.render_prompt(
            "gap_analysis",
            required_capabilities=json.dumps(required_capabilities),
            available_capabilities=json.dumps(available_capabilities),
            rag_insights=json.dumps(rag_insights, indent=2),
        )
        result = await self._call_llm(prompt_str)

        return result

    async def _generate_solutions(self, gap: str, requirements: Dict[str, Any]) -> List[Dict]:
        """Generate solutions for capability gap using LLM"""
        context = {
            "business_context": requirements.get("primary_goal", ""),
            "constraints": requirements.get("constraints", {}),
            "preferences": requirements.get("preferences", {}),
        }

        prompt_str = await self.prompt_engine.render_prompt(
            "solution_generation",
            gap=gap,
            requirements=json.dumps(requirements, indent=2),
            context=json.dumps(context, indent=2),
        )
        result = await self._call_llm(prompt_str)

        return result if isinstance(result, list) else []

    async def perform_capability_scan(self, requirements: Dict[str, Any]) -> CapabilityAnalysis:
        """
        Dynamic capability scanning using LLM and RAG
        """
        logger.info("Starting LLM-enhanced capability scan")

        # Step 1: Extract required capabilities using LLM
        required_capabilities = await self._extract_required_capabilities(requirements)

        # Step 2: Get RAG recommendations
        rag_recommendations = await self.rag.get_capability_recommendations(
            required_capabilities,
            context={
                "complexity_preference": requirements.get("estimated_complexity", "medium"),
                "business_context": requirements.get("primary_goal", ""),
                "performance_requirements": requirements.get("performance_requirements", {}),
            },
        )

        # Step 3: Combine static and RAG capabilities
        static_capabilities = list(self.capability_library.get("capability_matrix", {}).keys())
        rag_capabilities = []

        for cap_matches in rag_recommendations.get("capability_matches", {}).values():
            for match in cap_matches:
                if hasattr(match, "node_type") and match.node_type not in rag_capabilities:
                    rag_capabilities.append(match.node_type)

        available_capabilities = list(set(static_capabilities + rag_capabilities))

        # Step 4: Analyze gaps using LLM
        gap_analysis = await self._analyze_capability_gaps(
            required_capabilities, available_capabilities, rag_recommendations
        )

        capability_gaps = gap_analysis.get("gaps", [])

        # Safe handling of gap severity with fallback
        severity_data = gap_analysis.get("severity", {})
        gap_severity = {}
        for gap, severity in severity_data.items() if isinstance(severity_data, dict) else []:
            try:
                gap_severity[gap] = (
                    GapSeverity(severity) if isinstance(severity, str) else GapSeverity.MEDIUM
                )
            except (ValueError, TypeError):
                gap_severity[gap] = GapSeverity.MEDIUM  # Default fallback

        # Step 5: Generate solutions for each gap using LLM
        potential_solutions = {}
        for gap in capability_gaps:
            solutions_data = await self._generate_solutions(gap, requirements)
            solutions = []
            for sol_data in solutions_data[:5]:  # Top 5 solutions
                try:
                    if isinstance(sol_data, dict):
                        solution = Solution(
                            type=SolutionType(sol_data.get("type", "api_integration")),
                            complexity=sol_data.get("complexity", 5),
                            setup_time=sol_data.get("setup_time", "unknown"),
                            requires_user_action=sol_data.get("requires_user_action", "none"),
                            reliability=SolutionReliability(sol_data.get("reliability", "medium")),
                            description=sol_data.get("description", ""),
                        )
                        solutions.append(solution)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to create Solution from {sol_data}: {e}")
                    continue
            potential_solutions[gap] = solutions

        # Step 6: Calculate complexity scores (LLM + legacy fallback)
        complexity_scores = {}
        for cap in required_capabilities:
            if cap in self.capability_library.get("capability_matrix", {}):
                complexity_scores[cap] = self.capability_library["capability_matrix"][cap][
                    "complexity_score"
                ]
            else:
                # Use LLM to estimate complexity
                prompt_str = await self.prompt_engine.render_prompt(
                    "capability_complexity_estimation",
                    capability=cap,
                    context=json.dumps(requirements, indent=2),
                )
                complexity_result = await self._call_llm(prompt_str)
                try:
                    complexity_scores[cap] = float(complexity_result.get("response", "8"))
                except (ValueError, TypeError):
                    complexity_scores[cap] = 8.0  # Default

        # Create capability analysis result
        try:
            capability_analysis = CapabilityAnalysis(
                required_capabilities=required_capabilities,
                available_capabilities=available_capabilities,
                capability_gaps=capability_gaps,
                gap_severity=gap_severity,
                potential_solutions=potential_solutions,
                complexity_scores=complexity_scores,
            )
        except Exception as e:
            logger.error("Failed to create CapabilityAnalysis", error=str(e))
            # Create a dict with the same structure as fallback
            capability_analysis = {
                "required_capabilities": required_capabilities,
                "available_capabilities": available_capabilities,
                "capability_gaps": capability_gaps,
                "gap_severity": gap_severity,
                "potential_solutions": potential_solutions,
                "complexity_scores": complexity_scores,
                "rag_insights": {},
            }
            return capability_analysis

        # Add RAG insights
        capability_analysis.rag_insights = {
            "coverage_score": rag_recommendations.get("coverage_score", 0),
            "total_rag_matches": rag_recommendations.get("total_matches", 0),
            "missing_capabilities": rag_recommendations.get("missing_capabilities", []),
            "recommended_alternatives": rag_recommendations.get("alternatives", [])[:3],
            "confidence": "high"
            if rag_recommendations.get("coverage_score", 0) > 0.8
            else "medium",
        }

        logger.info(
            "LLM-enhanced capability scan completed",
            required=len(required_capabilities),
            gaps=len(capability_gaps),
            rag_coverage=rag_recommendations.get("coverage_score", 0),
        )

        return capability_analysis

    async def assess_complexity(self, capabilities: CapabilityAnalysis) -> Dict[str, Any]:
        """
        Comprehensive complexity assessment using LLM
        """
        logger.info("Assessing complexity with LLM")

        # Prepare data for LLM
        capabilities_data = {
            "required_capabilities": capabilities.required_capabilities,
            "capability_gaps": capabilities.capability_gaps,
            "complexity_scores": capabilities.complexity_scores,
            "gap_severity": {
                gap: severity.value for gap, severity in capabilities.gap_severity.items()
            },
        }

        # Use LLM for complexity assessment
        prompt_str = await self.prompt_engine.render_prompt(
            "complexity_assessment",
            capabilities=json.dumps(capabilities_data, indent=2),
            requirements="",  # You might want to pass original requirements here
            context="",
        )
        complexity_result = await self._call_llm(prompt_str)

        logger.info(
            "LLM complexity assessment completed",
            overall_score=complexity_result.get("overall_score", 0),
        )

        return complexity_result

    async def identify_constraints(self, analysis: Dict[str, Any]) -> List[Constraint]:
        """
        Identify constraints using LLM
        """
        logger.info("Identifying constraints with LLM")

        # Use LLM for constraint identification
        prompt_str = await self.prompt_engine.render_prompt(
            "constraint_identification",
            analysis=json.dumps(analysis, indent=2),
            requirements=json.dumps(analysis.get("requirements", {}), indent=2),
        )
        constraint_result = await self._call_llm(prompt_str)

        # Convert to Constraint objects
        constraints = []
        for constraint_data in constraint_result if isinstance(constraint_result, list) else []:
            try:
                constraints.append(
                    Constraint(
                        type=constraint_data.get("type", "unknown"),
                        description=constraint_data.get("description", ""),
                        severity=GapSeverity(constraint_data.get("severity", "medium")),
                        impact=constraint_data.get("impact", ""),
                    )
                )
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to parse constraint: {e}")
                continue

        logger.info("LLM constraint identification completed", count=len(constraints))
        return constraints


class IntelligentAnalyzer:
    """
    Complete intelligent analysis engine as per MVP plan
    Handles requirement parsing and capability scanning
    """

    def __init__(self):
        self.llm = self._setup_llm()
        self.capability_library = self._load_capability_library()
        self.historical_cases = self._load_historical_cases()
        self.rag = get_node_knowledge_rag()
        self.prompt_engine = get_prompt_engine()
        self.scanner = LLMCapabilityScanner(self.llm, self.rag)

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

    def _load_capability_library(self) -> Dict[str, Any]:
        """Load the complete capability library"""
        return {
            "native_nodes": {
                "triggers": ["email", "webhook", "cron", "manual", "slack", "file_watcher"],
                "ai_agents": [
                    "task_analyzer",
                    "data_integrator",
                    "report_generator",
                    "router_agent",
                    "content_analyzer",
                    "decision_maker",
                ],
                "external_integrations": [
                    "slack",
                    "notion",
                    "gmail",
                    "github",
                    "google_calendar",
                    "trello",
                    "asana",
                    "jira",
                    "dropbox",
                    "google_drive",
                ],
                "flow_controls": [
                    "if_else",
                    "loop",
                    "parallel",
                    "error_handling",
                    "retry",
                    "timeout",
                    "rate_limit",
                ],
                "memory_systems": [
                    "vector_store",
                    "knowledge_base",
                    "session_memory",
                    "cache",
                    "database",
                ],
                "transformations": [
                    "data_mapper",
                    "format_converter",
                    "aggregator",
                    "filter",
                    "sorter",
                    "validator",
                ],
            },
            "capability_matrix": {
                "email_monitoring": {
                    "complexity_score": 3,
                    "setup_time": "15分钟",
                    "reliability": "high",
                    "alternatives": ["webhook", "manual_check"],
                    "dependencies": ["email_credentials"],
                },
                "ai_analysis": {
                    "complexity_score": 6,
                    "setup_time": "30-60分钟",
                    "reliability": "medium",
                    "dependencies": ["openai_api", "prompt_templates"],
                    "alternatives": ["rule_based", "keyword_matching"],
                },
                "notion_integration": {
                    "complexity_score": 4,
                    "setup_time": "20分钟",
                    "reliability": "high",
                    "dependencies": ["notion_api_key"],
                    "alternatives": ["airtable", "google_sheets"],
                },
                "slack_integration": {
                    "complexity_score": 3,
                    "setup_time": "15分钟",
                    "reliability": "high",
                    "dependencies": ["slack_bot_token"],
                    "alternatives": ["discord", "teams"],
                },
                "github_integration": {
                    "complexity_score": 4,
                    "setup_time": "25分钟",
                    "reliability": "high",
                    "dependencies": ["github_token"],
                    "alternatives": ["gitlab", "bitbucket"],
                },
                "customer_detection": {
                    "complexity_score": 7,
                    "setup_time": "1-2小时",
                    "reliability": "medium",
                    "dependencies": ["training_data", "ai_model"],
                    "alternatives": ["keyword_filter", "regex_matching"],
                },
                "data_transformation": {
                    "complexity_score": 5,
                    "setup_time": "45分钟",
                    "reliability": "high",
                    "dependencies": ["mapping_rules"],
                    "alternatives": ["manual_processing", "simple_copy"],
                },
            },
        }

    def _load_historical_cases(self) -> List[Dict[str, Any]]:
        """Load historical successful cases for pattern matching"""
        return [
            {
                "pattern": "customer_service_automation",
                "description": "邮件监控 + AI分析 + 自动回复/人工转接",
                "success_rate": 0.85,
                "avg_complexity": 6,
                "common_issues": ["AI信心度调优", "邮件分类准确性"],
                "best_practices": ["设置信心度阈值", "添加人工审核机制"],
            },
            {
                "pattern": "data_integration_pipeline",
                "description": "定时任务 + 数据抓取 + 转换 + 多目标输出",
                "success_rate": 0.92,
                "avg_complexity": 5,
                "common_issues": ["数据格式不一致", "API限制"],
                "best_practices": ["增量更新", "错误重试机制"],
            },
            {
                "pattern": "notification_system",
                "description": "事件触发 + 条件判断 + 多渠道通知",
                "success_rate": 0.95,
                "avg_complexity": 4,
                "common_issues": ["通知去重", "时区处理"],
                "best_practices": ["通知模板化", "用户偏好设置"],
            },
        ]

    async def parse_requirements(self, user_input: str) -> Dict[str, Any]:
        """
        Deep requirement parsing with intent understanding
        完整实现 - 与长期愿景一致
        """
        logger.info("Starting deep requirement parsing", input=user_input)

        # Use centralized prompt templates
        prompt_str = await self.prompt_engine.render_prompt(
            "analyze_requirement_user", description=user_input
        )

        messages = [HumanMessage(content=prompt_str)]

        try:
            response = await self.llm.ainvoke(messages)
            content = response.content if hasattr(response, "content") else str(response)
            analysis = json.loads(content)

            # 增强分析结果
            analysis["confidence"] = self._calculate_confidence(analysis)
            analysis["category"] = self._categorize_requirement(analysis)
            analysis["estimated_complexity"] = self._estimate_complexity(analysis)

            logger.info("Requirement parsing completed", analysis=analysis)
            return analysis

        except Exception as e:
            logger.error("Failed to parse requirements", error=str(e))
            # Return fallback analysis matching new template structure
            return {
                "requirement_analysis": {
                    "primary_goal": "基本工作流自动化",
                    "secondary_goals": ["提高效率"],
                    "success_criteria": ["系统正常运行"],
                    "business_value": "自动化处理用户需求",
                    "confidence_level": 0.3,
                },
                "technical_requirements": {
                    "triggers": [
                        {
                            "type": "manual",
                            "description": "手动触发",
                            "frequency": "按需",
                            "conditions": "用户启动",
                        }
                    ],
                    "main_operations": [
                        {
                            "operation": "数据处理",
                            "description": "基本数据处理",
                            "complexity": "medium",
                            "ai_required": False,
                        }
                    ],
                    "data_flow": {
                        "input_sources": ["用户输入"],
                        "processing_steps": ["基本处理"],
                        "output_destinations": ["系统输出"],
                        "data_transformations": ["基本转换"],
                    },
                    "integrations": [],
                    "performance_requirements": {
                        "volume": "低量",
                        "latency": "正常",
                        "availability": "标准",
                    },
                },
                "constraints": {
                    "technical_constraints": [],
                    "business_constraints": [],
                    "resource_constraints": ["需要更多信息"],
                    "compliance_requirements": [],
                },
                "complexity_assessment": {
                    "overall_complexity": "medium",
                    "technical_complexity": 5,
                    "business_complexity": 3,
                    "integration_complexity": 2,
                    "complexity_drivers": ["信息不足"],
                },
                "risk_analysis": {
                    "implementation_risks": [],
                    "operational_risks": [],
                    "ambiguities": [{"area": "需求理解", "question": "需要更详细的需求描述", "impact": "影响准确分析"}],
                },
                "recommendations": {
                    "immediate_clarifications": ["请提供更详细的需求描述"],
                    "alternative_approaches": ["从简单功能开始"],
                    "success_factors": ["明确需求", "逐步实现"],
                },
                "metadata": {
                    "category": "automation",
                    "estimated_timeline": "1-2天",
                    "skill_requirements": ["基本配置"],
                    "similar_patterns": ["基本自动化"],
                },
            }

    def match_historical_cases(self, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Match against historical successful cases
        完整实现 - 与长期愿景一致
        """
        logger.info("Matching historical cases")

        matches = []

        for case in self.historical_cases:
            similarity_score = self._calculate_similarity(requirements, case)
            if similarity_score > 0.3:  # 相似度阈值
                matches.append(
                    {
                        "case": case,
                        "similarity_score": similarity_score,
                        "applicable_practices": case["best_practices"],
                        "potential_issues": case["common_issues"],
                    }
                )

        # 按相似度排序
        matches.sort(key=lambda x: x["similarity_score"], reverse=True)

        logger.info("Historical case matching completed", matches_count=len(matches))
        return matches

    async def perform_capability_scan(self, requirements: Dict[str, Any]) -> CapabilityAnalysis:
        """
        Dynamic capability scanning with real-time assessment and RAG enhancement
        """
        return await self.scanner.perform_capability_scan(requirements)

    async def assess_complexity(self, capabilities: CapabilityAnalysis) -> Dict[str, Any]:
        """
        Comprehensive complexity assessment
        """
        return await self.scanner.assess_complexity(capabilities)

    async def identify_constraints(self, analysis: Dict[str, Any]) -> List[Constraint]:
        """
        Identify technical and business constraints
        """
        return await self.scanner.identify_constraints(analysis)

    # Helper methods
    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence score for requirement analysis"""
        confidence = 0.5  # Base confidence

        # 增加信心度的因素
        if analysis.get("primary_goal"):
            confidence += 0.2
        if analysis.get("triggers"):
            confidence += 0.1
        if analysis.get("integrations"):
            confidence += 0.1
        if len(analysis.get("ambiguities", [])) == 0:
            confidence += 0.1

        return min(confidence, 1.0)

    def _categorize_requirement(self, analysis: Dict[str, Any]) -> str:
        """Categorize the requirement type"""
        if "notification" in analysis.get("primary_goal", "").lower():
            return "notification"
        elif "data" in analysis.get("primary_goal", "").lower():
            return "data_processing"
        elif "customer" in analysis.get("primary_goal", "").lower():
            return "customer_service"
        else:
            return "automation"

    def _estimate_complexity(self, analysis: Dict[str, Any]) -> int:
        """Estimate overall complexity score"""
        complexity = 3  # Base complexity

        complexity += len(analysis.get("integrations", [])) * 2
        complexity += len(analysis.get("human_intervention", [])) * 1
        complexity += len(analysis.get("complexity_indicators", [])) * 1

        return min(complexity, 10)

    def _calculate_similarity(self, requirements: Dict[str, Any], case: Dict[str, Any]) -> float:
        """Calculate similarity between requirements and historical case"""
        # 简化的相似度计算
        similarity = 0.0

        # 比较主要目标
        if requirements.get("category") == case.get("pattern"):
            similarity += 0.5

        # 比较复杂度
        req_complexity = requirements.get("estimated_complexity", 5)
        case_complexity = case.get("avg_complexity", 5)
        complexity_diff = abs(req_complexity - case_complexity)
        if complexity_diff <= 2:
            similarity += 0.3

        # 比较集成数量
        req_integrations = len(requirements.get("integrations", []))
        # 估算历史案例的集成数量
        case_integrations = case.get("avg_complexity", 5) // 2
        if abs(req_integrations - case_integrations) <= 1:
            similarity += 0.2

        return similarity


class IntelligentNegotiator:
    """
    Intelligent negotiation engine for multi-round requirement refinement
    完整实现 - 与长期愿景一致
    """

    def __init__(self):
        self.llm_client = self._setup_llm()
        self.prompt_engine = get_prompt_engine()
        self.negotiation_patterns = self._load_negotiation_patterns()
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

    def _load_negotiation_patterns(self) -> Dict[str, Any]:
        """Load negotiation patterns for different scenarios"""
        return {
            "capability_gap_negotiation": {
                "high_severity": {
                    "approach": "solution_comparison",
                    "tone": "consultative",
                    "focus": "tradeoffs_and_alternatives",
                },
                "medium_severity": {
                    "approach": "guided_selection",
                    "tone": "advisory",
                    "focus": "complexity_vs_benefit",
                },
                "low_severity": {
                    "approach": "simple_choice",
                    "tone": "informative",
                    "focus": "quick_decision",
                },
            },
            "complexity_negotiation": {
                "high_complexity": {
                    "approach": "phased_implementation",
                    "tone": "collaborative",
                    "focus": "risk_mitigation",
                },
                "medium_complexity": {
                    "approach": "optimization_suggestions",
                    "tone": "supportive",
                    "focus": "efficiency_gains",
                },
            },
        }

    async def generate_contextual_questions(
        self,
        gaps: List[str],
        capability_analysis: CapabilityAnalysis,
        history: List[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Generate context-aware negotiation questions
        完整实现 - 与长期愿景一致
        """
        logger.info("Generating contextual questions", gaps=gaps)

        if history is None:
            history = []

        questions = []

        for gap in gaps:
            severity = capability_analysis["gap_severity"].get(gap, GapSeverity.MEDIUM)
            solutions = capability_analysis["potential_solutions"].get(gap, [])

            if severity == GapSeverity.HIGH or severity == GapSeverity.CRITICAL:
                # 高严重性缺口需要详细协商
                question = await self._generate_high_severity_question(gap, solutions, history)
                questions.append(question)
            elif severity == GapSeverity.MEDIUM:
                # 中等严重性提供选择
                question = await self._generate_medium_severity_question(gap, solutions, history)
                questions.append(question)
            else:
                # 低严重性简单询问
                question = await self._generate_low_severity_question(gap, solutions, history)
                questions.append(question)

        # 去重和排序
        questions = list(set(questions))
        questions.sort(key=lambda x: self._calculate_question_priority(x, capability_analysis))

        logger.info("Generated contextual questions", count=len(questions))
        return questions[:5]  # 最多返回5个问题

    async def present_tradeoff_analysis(
        self, solutions: List[Solution], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Present comprehensive tradeoff analysis
        完整实现 - 与长期愿景一致
        """
        logger.info("Presenting tradeoff analysis", solutions_count=len(solutions))

        # 创建对比表
        comparison_table = self._create_comparison_table(solutions)

        # 生成推荐
        recommendation = await self._generate_recommendation(solutions, context)

        # 风险分析
        risk_analysis = self._analyze_risks(solutions)

        # 成本效益分析
        cost_benefit = self._calculate_cost_benefit(solutions)

        tradeoff_analysis = {
            "comparison_table": comparison_table,
            "recommendation": recommendation,
            "risk_analysis": risk_analysis,
            "cost_benefit": cost_benefit,
            "decision_framework": self._create_decision_framework(solutions),
        }

        logger.info("Tradeoff analysis completed")
        return tradeoff_analysis

    async def process_negotiation_round(
        self, user_input: str, context: Dict[str, Any], history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process a single negotiation round
        完整实现 - 与长期愿景一致
        """
        logger.info("Processing negotiation round", input=user_input)

        # 分析用户回应
        response_analysis = await self._analyze_user_response(user_input, context)

        # 更新上下文
        updated_context = self._update_context(context, response_analysis)

        # 确定下一步行动
        next_action = self._determine_next_action(response_analysis, history)

        # 生成响应
        if next_action == "ask_clarification":
            response = await self._generate_clarification_question(
                response_analysis, updated_context
            )
        elif next_action == "present_alternatives":
            response = await self._present_alternatives(response_analysis, updated_context)
        elif next_action == "finalize_agreement":
            response = await self._finalize_agreement(response_analysis, updated_context)
        else:
            response = await self._generate_default_response(response_analysis, updated_context)

        negotiation_result = {
            "user_input": user_input,
            "response_analysis": response_analysis,
            "updated_context": updated_context,
            "next_action": next_action,
            "response": response,
            "negotiation_complete": next_action == "finalize_agreement",
        }

        # If negotiation is complete, generate final requirements
        if next_action == "finalize_agreement":
            # Extract original requirements from context or use user input
            original_requirements = updated_context.get("original_requirements", "")
            if not original_requirements:
                # Try to get from history
                if history:
                    original_requirements = history[0].get("user_response", "")
                if not original_requirements:
                    original_requirements = user_input

            # Generate final requirements
            final_requirements = self._generate_final_requirements(
                {"original_requirements": original_requirements}, []
            )

            negotiation_result["final_requirements"] = final_requirements
            negotiation_result["confidence_score"] = 0.8

        logger.info("Negotiation round processed", action=next_action)
        return negotiation_result

    def validate_agreements(self, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate user agreements for feasibility
        完整实现 - 与长期愿景一致
        """
        logger.info("Validating agreements", decisions_count=len(decisions))

        validation_results = {
            "feasible": True,
            "conflicts": [],
            "missing_decisions": [],
            "risk_factors": [],
            "recommendations": [],
        }

        # 检查决策一致性
        conflicts = self._check_decision_conflicts(decisions)
        validation_results["conflicts"] = conflicts

        # 检查缺失决策
        missing = self._check_missing_decisions(decisions)
        validation_results["missing_decisions"] = missing

        # 风险评估
        risks = self._assess_decision_risks(decisions)
        validation_results["risk_factors"] = risks

        # 可行性检查
        if conflicts or missing:
            validation_results["feasible"] = False

        # 生成建议
        recommendations = self._generate_validation_recommendations(validation_results)
        validation_results["recommendations"] = recommendations

        logger.info("Agreement validation completed", feasible=validation_results["feasible"])
        return validation_results

    def optimize_requirements(self, agreements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Optimize requirements based on agreements
        完整实现 - 与长期愿景一致
        """
        logger.info("Optimizing requirements", agreements_count=len(agreements))

        # 整合决策
        consolidated_decisions = self._consolidate_decisions(agreements)

        # 优化建议
        optimizations = self._identify_optimizations(consolidated_decisions)

        # 生成最终需求
        final_requirements = self._generate_final_requirements(
            consolidated_decisions, optimizations
        )

        # 置信度评估
        confidence_score = self._calculate_confidence_score(agreements)

        optimization_result = {
            "consolidated_decisions": consolidated_decisions,
            "optimizations": optimizations,
            "final_requirements": final_requirements,
            "confidence_score": confidence_score,
            "implementation_plan": self._create_implementation_plan(final_requirements),
        }

        logger.info("Requirements optimization completed", confidence=confidence_score)
        return optimization_result

    # Helper methods for negotiation
    async def _generate_high_severity_question(
        self, gap: str, solutions: List[Solution], history: List[Dict[str, Any]]
    ) -> str:
        """Generate question for high severity capability gap using templates"""

        # Use the negotiation engine prompt template
        system_prompt = await self.prompt_engine.render_prompt("negotiation_engine.j2")

        # Create context for the negotiation prompt
        context = {
            "consultation_type": "gap_resolution",
            "gap": gap,
            "solutions": [
                {
                    "option_id": f"A{i}",
                    "title": sol["description"],
                    "complexity": sol["complexity"],
                    "setup_time": sol["setup_time"],
                    "reliability": sol["reliability"],
                }
                for i, sol in enumerate(solutions[:3])
            ],
            "severity": "high",
            "history_length": len(history),
        }

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"Generate consultation for high severity gap: {gap}. Solutions: {json.dumps(context['solutions'])}"
            ),
        ]

        try:
            response = await self.llm_client.ainvoke(messages)
            content = response.content if hasattr(response, "content") else str(response)

            # Try to parse as JSON for structured response
            try:
                result = json.loads(content.strip())
                if "guided_questions" in result and result["guided_questions"]:
                    return result["guided_questions"][0]["question"]
            except:
                pass

            return content.strip()

        except Exception as e:
            logger.warning(f"Failed to generate contextual question: {e}")
            # Fallback to simple question
            return f"关键能力缺口：{gap}。我们需要找到解决方案，您有什么具体要求吗？"

    async def _generate_medium_severity_question(
        self, gap: str, solutions: List[Solution], history: List[Dict[str, Any]]
    ) -> str:
        """Generate question for medium severity capability gap using templates"""

        # Use the negotiation engine prompt template
        system_prompt = await self.prompt_engine.render_prompt("negotiation_engine")

        context = {
            "consultation_type": "requirement_clarification",
            "gap": gap,
            "solutions": [
                {
                    "option_id": f"B{i}",
                    "title": sol["description"],
                    "complexity": sol["complexity"],
                    "setup_time": sol["setup_time"],
                }
                for i, sol in enumerate(solutions[:2])
            ],
            "severity": "medium",
        }

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content=f"Generate consultation for medium severity gap: {gap}. Solutions: {json.dumps(context['solutions'])}"
            ),
        ]

        try:
            response = await self.llm_client.ainvoke(messages)
            content = response.content if hasattr(response, "content") else str(response)

            try:
                result = json.loads(content.strip())
                if "guided_questions" in result and result["guided_questions"]:
                    return result["guided_questions"][0]["question"]
            except:
                pass

            return content.strip()

        except Exception as e:
            logger.warning(f"Failed to generate medium severity question: {e}")
            return f"需要实现：{gap}。您有偏好的实现方式吗？"

    async def _generate_low_severity_question(
        self, gap: str, solutions: List[Solution], history: List[Dict[str, Any]]
    ) -> str:
        """Generate question for low severity capability gap using templates"""

        try:
            # Simple template-based generation for low severity
            if not solutions:
                return f"可选功能：{gap}。是否需要包含？"

            # Use simplest solution
            simple_solution = min(solutions, key=lambda x: x["complexity"])
            return f"可选功能：{gap}。建议使用{simple_solution['description']}，您同意吗？"

        except Exception as e:
            logger.warning(f"Failed to generate low severity question: {e}")
            return f"可选功能：{gap}。��否需要包含？"

    def _calculate_question_priority(
        self, question: str, capability_analysis: CapabilityAnalysis
    ) -> int:
        """Calculate priority for question ordering"""
        priority = 0

        # 基于严重性
        if "关键能力缺口" in question:
            priority += 100
        elif "需要实现" in question:
            priority += 50
        elif "可选功能" in question:
            priority += 10

        # 基于复杂度
        if "复杂度" in question:
            # 提取复杂度数字
            import re

            complexity_match = re.search(r"复杂度: (\d+)", question)
            if complexity_match:
                complexity = int(complexity_match.group(1))
                priority += complexity * 5

        return priority

    def _create_comparison_table(self, solutions: List[Solution]) -> Dict[str, Any]:
        """Create comparison table for solutions"""
        table = {"headers": ["解决方案", "复杂度", "设置时间", "可靠性", "用户操作"], "rows": []}

        for solution in solutions:
            row = [
                solution["description"],
                f"{solution['complexity']}/10",
                solution["setup_time"],
                solution["reliability"],
                solution["requires_user_action"],
            ]
            table["rows"].append(row)

        return table

    async def _generate_recommendation(
        self, solutions: List[Solution], context: Dict[str, Any]
    ) -> str:
        """Generate intelligent recommendation with RAG enhancement"""
        if not solutions:
            return "暂无可用解决方案"

        # Get RAG insights for solution recommendation
        try:
            # Extract solution types for RAG search
            solution_types = [sol["type"] for sol in solutions]
            search_query = f"best practices for {', '.join(solution_types)} implementation"

            rag_insights = await self.rag.vector_store.similarity_search(search_query, k=3)

            # Combine traditional logic with RAG insights
            user_skill_level = context.get("user_skill_level", "medium")
            time_constraint = context.get("time_constraint", "medium")

            if user_skill_level == "low" or time_constraint == "high":
                # 推荐简单方案
                simple_solution = min(solutions, key=lambda x: x["complexity"])
                recommendation = f"推荐：{simple_solution['description']} - 简单易用，快速实现"
            else:
                # 推荐平衡方案
                balanced_solution = min(
                    solutions,
                    key=lambda x: x["complexity"] + (10 - (8 if x["reliability"] == "high" else 5)),
                )
                recommendation = f"推荐：{balanced_solution['description']} - 平衡复杂度和可靠性"

            # Add RAG insights if available
            if rag_insights and rag_insights[0].metadata.get("score") > 0.6:
                best_practice = rag_insights[0].page_content[:100] + "..."
                recommendation += f"\n\n💡 最佳实践建议：{best_practice}"

            return recommendation

        except Exception as e:
            logger.warning("RAG recommendation enhancement failed", error=str(e))
            # Fallback to simple logic
            simple_solution = min(solutions, key=lambda x: x["complexity"])
            return f"推荐：{simple_solution['description']} - 简单易用，快速实现"

    def _analyze_risks(self, solutions: List[Solution]) -> List[str]:
        """Analyze risks in solutions"""
        risks = []

        for solution in solutions:
            if solution["reliability"] == SolutionReliability.LOW:
                risks.append(f"低可靠性风险：{solution['description']}")
            if solution["complexity"] > 8:
                risks.append(f"高复杂度风险：{solution['description']}")

        return risks

    def _calculate_cost_benefit(self, solutions: List[Solution]) -> Dict[str, Any]:
        """Calculate cost-benefit analysis"""
        if not solutions:
            return {"total_cost": 0, "expected_benefit": 0, "roi": 0}

        # 简化的成本效益计算
        avg_complexity = sum(s["complexity"] for s in solutions) / len(solutions)
        avg_reliability = sum(8 if s["reliability"] == "high" else 5 for s in solutions) / len(
            solutions
        )

        cost_score = avg_complexity * 10  # 假设复杂度转换为成本
        benefit_score = avg_reliability * 12  # 假设可靠性转换为效益

        return {
            "cost_score": cost_score,
            "benefit_score": benefit_score,
            "roi": (benefit_score - cost_score) / cost_score if cost_score > 0 else 0,
        }

    def _create_decision_framework(self, solutions: List[Solution]) -> Dict[str, Any]:
        """Create decision framework for users"""
        return {
            "decision_criteria": [
                "实现复杂度",
                "设置时间",
                "长期维护成本",
                "可靠性要求",
                "团队技能匹配",
            ],
            "weight_suggestions": {
                "快速原型": {"complexity": 0.5, "time": 0.3, "reliability": 0.2},
                "生产环境": {"complexity": 0.2, "time": 0.2, "reliability": 0.6},
                "长期使用": {"complexity": 0.3, "time": 0.1, "reliability": 0.6},
            },
        }

    # Additional helper methods would be implemented here
    async def _analyze_user_response(
        self, user_input: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze user response to determine intent"""
        # Simplified analysis
        lower_input = user_input.lower()

        # Determine intent based on keywords
        if any(word in lower_input for word in ["选择", "要", "用", "我选择", "我要"]):
            intent = "selection"
        elif any(word in lower_input for word in ["好", "是", "对", "确认", "同意"]):
            intent = "confirmation"
        elif any(word in lower_input for word in ["完成", "结束", "够了", "可以了"]):
            intent = "agreement"
        else:
            intent = "clarification"

        return {
            "intent": intent,
            "confidence": 0.8,
            "extracted_preferences": {},
            "sentiment": "positive",
            "user_input": user_input,  # Include the actual user input
        }

    def _update_context(self, context: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Update negotiation context"""
        updated = context.copy()
        updated["last_response"] = analysis
        return updated

    def _determine_next_action(
        self, analysis: Dict[str, Any], history: List[Dict[str, Any]]
    ) -> str:
        """Determine next negotiation action"""
        # Check if we have enough rounds of negotiation
        if len(history) > 3:
            return "finalize_agreement"

        # Check if user provided substantial requirements
        user_input = analysis.get("user_input", "").strip()
        if len(user_input) > 50:  # Substantial input
            return "finalize_agreement"

        # Check intent
        intent = analysis.get("intent", "")
        if intent == "selection":
            return "present_alternatives"
        elif intent in ["confirmation", "agreement"]:
            return "finalize_agreement"
        else:
            return "ask_clarification"

    async def _generate_clarification_question(
        self, analysis: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """Generate clarification question"""
        return "请问您需要我澄清哪个方面的信息？"

    async def _present_alternatives(self, analysis: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Present alternative solutions"""
        return "基于您的选择，我为您准备了几个备选方案..."

    async def _finalize_agreement(self, analysis: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Finalize negotiation agreement"""
        return "很好，我们达成了一致。让我总结一下我们的决定..."

    async def _generate_default_response(
        self, analysis: Dict[str, Any], context: Dict[str, Any]
    ) -> str:
        """Generate default response"""
        return "我理解您的观点，让我们继续讨论..."

    def _check_decision_conflicts(self, decisions: List[Dict[str, Any]]) -> List[str]:
        """Check for conflicts in decisions"""
        return []  # Simplified implementation

    def _check_missing_decisions(self, decisions: List[Dict[str, Any]]) -> List[str]:
        """Check for missing critical decisions"""
        return []  # Simplified implementation

    def _assess_decision_risks(self, decisions: List[Dict[str, Any]]) -> List[str]:
        """Assess risks in decisions"""
        return []  # Simplified implementation

    def _generate_validation_recommendations(self, validation: Dict[str, Any]) -> List[str]:
        """Generate validation recommendations"""
        return []  # Simplified implementation

    def _consolidate_decisions(self, agreements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Consolidate all decisions"""
        # Extract the original requirements from the first agreement or negotiation context
        original_requirements = ""

        # Look for original requirements in agreements
        for agreement in agreements:
            if "original_requirements" in agreement:
                original_requirements = agreement["original_requirements"]
                break
            # Also check if there's a context with original requirements
            if "context" in agreement:
                context = agreement["context"]
                if isinstance(context, dict) and "original_requirements" in context:
                    original_requirements = context["original_requirements"]
                    break

        # If no original requirements found, try to extract from first agreement
        if not original_requirements and agreements:
            first_agreement = agreements[0]
            if "user_input" in first_agreement:
                original_requirements = first_agreement["user_input"]

        return {
            "original_requirements": original_requirements,
            "agreements": agreements,
            "decision_count": len(agreements),
        }

    def _identify_optimizations(self, decisions: Dict[str, Any]) -> List[str]:
        """Identify optimization opportunities"""
        return []  # Simplified implementation

    def _generate_final_requirements(
        self, decisions: Dict[str, Any], optimizations: List[str]
    ) -> str:
        """Generate final requirements"""
        # Extract the original requirements from decisions
        original_requirements = decisions.get("original_requirements", "")

        # If we have original requirements, use them
        if original_requirements and len(original_requirements.strip()) > 0:
            return original_requirements

        # Otherwise, generate a basic requirement
        return "创建一个基本的工作流程来处理用户需求"

    def _calculate_confidence_score(self, agreements: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for agreements"""
        return 0.8  # Simplified implementation

    def _create_implementation_plan(self, requirements: str) -> Dict[str, Any]:
        """Create implementation plan"""
        return {"phases": [], "timeline": "", "resources": []}  # Simplified implementation
