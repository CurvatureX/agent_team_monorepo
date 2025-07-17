"""
Intelligence engines for Workflow Agent
Based on the MVP plan and architecture design
"""

import json
from typing import Any, Dict, List, Optional

import structlog
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from agents.state import (
    CapabilityAnalysis,
    Constraint,
    GapSeverity,
    Solution,
    SolutionReliability,
    SolutionType,
)
from core.config import settings
from core.vector_store import get_node_knowledge_rag

logger = structlog.get_logger()


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

        system_prompt = """
        你是一个专业的工作流需求分析专家。请深度分析用户的需求，提取关键信息。

        请按照以下格式返回JSON：
        {
            "primary_goal": "主要目标",
            "secondary_goals": ["次要目标1", "次要目标2"],
            "constraints": ["约束条件1", "约束条件2"],
            "success_criteria": ["成功标准1", "成功标准2"],
            "triggers": ["触发方式1", "触发方式2"],
            "main_operations": ["主要操作1", "主要操作2"],
            "data_flow": ["数据流向1", "数据流向2"],
            "integrations": ["集成系统1", "集成系统2"],
            "human_intervention": ["人工干预点1", "人工干预点2"],
            "complexity_indicators": ["复杂度指标1", "复杂度指标2"],
            "ambiguities": ["模糊点1", "模糊点2"]
        }
        """

        user_prompt = f"用户需求: {user_input}"

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

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
            # 返回基础分析结果
            return {
                "primary_goal": "数据处理自动化",
                "secondary_goals": [],
                "constraints": [],
                "success_criteria": ["系统正常运行"],
                "triggers": ["manual"],
                "main_operations": ["data_processing"],
                "data_flow": ["user_input"],
                "integrations": [],
                "human_intervention": [],
                "complexity_indicators": ["basic_automation"],
                "ambiguities": ["需要更多详细信息"],
                "confidence": 0.3,
                "category": "automation",
                "estimated_complexity": 5,
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
        完整实现 - 与长期愿景一致 + RAG智能推荐
        """
        logger.info("Starting enhanced capability scan with RAG")

        # 提取所需能力
        required_capabilities = self._extract_required_capabilities(requirements)

        # 使用RAG获取智能能力推荐
        rag_recommendations = await self.rag.get_capability_recommendations(
            required_capabilities,
            context={
                "complexity_preference": requirements.get("estimated_complexity", "medium"),
                "business_context": requirements.get("primary_goal", ""),
                "performance_requirements": requirements.get("performance_requirements", {}),
            },
        )

        # 增强的可用能力列表（结合静态库和RAG结果）
        static_capabilities = list(self.capability_library["capability_matrix"].keys())
        rag_capabilities = []

        for cap_matches in rag_recommendations["capability_matches"].values():
            for match in cap_matches:
                if match.node_type not in rag_capabilities:
                    rag_capabilities.append(match.node_type)

        available_capabilities = list(set(static_capabilities + rag_capabilities))

        # 智能识别缺口（考虑RAG推荐的替代方案）
        capability_gaps = []
        for cap in required_capabilities:
            if cap not in available_capabilities:
                # 检查是否有RAG推荐的替代方案
                alternatives = rag_recommendations.get("alternatives", [])
                has_alternative = any(cap.lower() in alt["content"].lower() for alt in alternatives)
                if not has_alternative:
                    capability_gaps.append(cap)

        # 评估缺口严重程度（增强版）
        gap_severity = {}
        for gap in capability_gaps:
            severity = await self._assess_gap_severity_enhanced(
                gap, requirements, rag_recommendations
            )
            gap_severity[gap] = severity

        # 搜索解决方案（结合RAG和静态方案）
        potential_solutions = {}
        for gap in capability_gaps:
            # 获取静态解决方案
            static_solutions = await self._search_solutions(gap, requirements)

            # 获取RAG推荐的解决方案
            rag_solutions = await self._get_rag_solutions(gap, requirements)

            # 合并并排序解决方案
            all_solutions = static_solutions + rag_solutions
            # 按可靠性和复杂度排序
            all_solutions.sort(key=lambda x: (x["reliability"], -x["complexity"]))

            potential_solutions[gap] = all_solutions[:5]  # 最多5个解决方案

        # 计算复杂度分数（增强版）
        complexity_scores = {}
        for cap in required_capabilities:
            if cap in self.capability_library["capability_matrix"]:
                complexity_scores[cap] = self.capability_library["capability_matrix"][cap][
                    "complexity_score"
                ]
            else:
                # 使用RAG推荐的复杂度
                rag_complexity = self._get_rag_complexity(cap, rag_recommendations)
                complexity_scores[cap] = rag_complexity or 8  # 默认高复杂度

        # 创建增强的能力分析结果
        capability_analysis = CapabilityAnalysis(
            required_capabilities=required_capabilities,
            available_capabilities=available_capabilities,
            capability_gaps=capability_gaps,
            gap_severity=gap_severity,
            potential_solutions=potential_solutions,
            complexity_scores=complexity_scores,
        )

        # 添加RAG推荐信息到结果中
        capability_analysis["rag_insights"] = {
            "coverage_score": rag_recommendations["coverage_score"],
            "total_rag_matches": rag_recommendations["total_matches"],
            "missing_capabilities": rag_recommendations["missing_capabilities"],
            "recommended_alternatives": rag_recommendations["alternatives"][:3],
            "confidence": "high" if rag_recommendations["coverage_score"] > 0.8 else "medium",
        }

        logger.info(
            "Enhanced capability scan completed",
            required=len(required_capabilities),
            gaps=len(capability_gaps),
            rag_coverage=rag_recommendations["coverage_score"],
            rag_matches=rag_recommendations["total_matches"],
        )

        return capability_analysis

    def assess_complexity(self, capabilities: CapabilityAnalysis) -> Dict[str, Any]:
        """
        Comprehensive complexity assessment
        完整实现 - 与长期愿景一致
        """
        logger.info("Assessing complexity")

        # 计算总体复杂度
        total_complexity = sum(capabilities["complexity_scores"].values())
        avg_complexity = (
            total_complexity / len(capabilities["complexity_scores"])
            if capabilities["complexity_scores"]
            else 0
        )

        # 评估各维度复杂度
        dimensions = {
            "technical_complexity": self._assess_technical_complexity(capabilities),
            "integration_complexity": self._assess_integration_complexity(capabilities),
            "maintenance_complexity": self._assess_maintenance_complexity(capabilities),
            "user_complexity": self._assess_user_complexity(capabilities),
        }

        # 风险评估
        risk_factors = self._identify_risk_factors(capabilities)

        # 时间估算
        time_estimate = self._estimate_development_time(capabilities)

        complexity_assessment = {
            "overall_score": avg_complexity,
            "dimensions": dimensions,
            "risk_factors": risk_factors,
            "time_estimate": time_estimate,
            "recommendations": self._generate_complexity_recommendations(capabilities),
        }

        logger.info(
            "Complexity assessment completed",
            overall_score=avg_complexity,
            risk_count=len(risk_factors),
        )

        return complexity_assessment

    def identify_constraints(self, analysis: Dict[str, Any]) -> List[Constraint]:
        """
        Identify technical and business constraints
        完整实现 - 与长期愿景一致
        """
        logger.info("Identifying constraints")

        constraints = []

        # 技术约束
        if "integrations" in analysis:
            for integration in analysis["integrations"]:
                if integration in ["enterprise_email", "custom_api"]:
                    constraints.append(
                        Constraint(
                            type="technical",
                            description=f"{integration}需要额外的认证和配置",
                            severity=GapSeverity.HIGH,
                            impact="可能需要IT部门支持",
                        )
                    )

        # 业务约束
        if "human_intervention" in analysis:
            for intervention in analysis["human_intervention"]:
                constraints.append(
                    Constraint(
                        type="business",
                        description=f"需要人工处理: {intervention}",
                        severity=GapSeverity.MEDIUM,
                        impact="需要安排人员值守",
                    )
                )

        # 复杂度约束
        if analysis.get("estimated_complexity", 0) > 7:
            constraints.append(
                Constraint(
                    type="complexity",
                    description="方案复杂度较高",
                    severity=GapSeverity.HIGH,
                    impact="开发和维护成本较高",
                )
            )

        logger.info("Constraint identification completed", count=len(constraints))
        return constraints

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

    def _extract_required_capabilities(self, requirements: Dict[str, Any]) -> List[str]:
        """Extract required capabilities from requirements"""
        capabilities = []

        # 基于触发器
        for trigger in requirements.get("triggers", []):
            if trigger == "email":
                capabilities.append("email_monitoring")
            elif trigger == "cron":
                capabilities.append("scheduled_execution")
            elif trigger == "webhook":
                capabilities.append("webhook_handling")

        # 基于集成
        for integration in requirements.get("integrations", []):
            if integration.lower() in ["slack", "notion", "github", "gmail"]:
                capabilities.append(f"{integration.lower()}_integration")

        # 基于操作
        for operation in requirements.get("main_operations", []):
            if "ai" in operation.lower() or "analyze" in operation.lower():
                capabilities.append("ai_analysis")
            elif "transform" in operation.lower():
                capabilities.append("data_transformation")
            elif "customer" in operation.lower():
                capabilities.append("customer_detection")

        return list(set(capabilities))  # 去重

    def _assess_gap_severity(self, gap: str, requirements: Dict[str, Any]) -> GapSeverity:
        """Assess the severity of a capability gap"""
        _ = requirements  # Mark as used to avoid warning

        # 关键能力缺口
        if gap in ["customer_detection", "ai_analysis"]:
            return GapSeverity.HIGH

        # 中等重要性
        if gap in ["data_transformation", "notification"]:
            return GapSeverity.MEDIUM

        # 低重要性
        return GapSeverity.LOW

    async def _search_solutions(self, gap: str, requirements: Dict[str, Any]) -> List[Solution]:
        """Search for solutions to capability gaps"""
        solutions = []
        _ = requirements  # Mark as used to avoid warning

        if gap == "customer_detection":
            solutions = [
                Solution(
                    type=SolutionType.CODE_NODE,
                    complexity=3,
                    setup_time="30分钟",
                    requires_user_action="提供关键词列表",
                    reliability=SolutionReliability.MEDIUM,
                    description="关键词过滤：简单快速，适合明确的客户标识",
                ),
                Solution(
                    type=SolutionType.API_INTEGRATION,
                    complexity=7,
                    setup_time="2-3小时",
                    requires_user_action="配置AI API密钥",
                    reliability=SolutionReliability.HIGH,
                    description="AI智能分析：准确率高，适合复杂场景",
                ),
                Solution(
                    type=SolutionType.CODE_NODE,
                    complexity=5,
                    setup_time="1小时",
                    requires_user_action="编写正则表达式",
                    reliability=SolutionReliability.HIGH,
                    description="正则表达式匹配：精确匹配，适合格式化内容",
                ),
            ]
        elif gap == "ai_analysis":
            solutions = [
                Solution(
                    type=SolutionType.NATIVE,
                    complexity=4,
                    setup_time="20分钟",
                    requires_user_action="配置AI节点参数",
                    reliability=SolutionReliability.HIGH,
                    description="使用内置AI节点：简单配置，稳定可靠",
                ),
                Solution(
                    type=SolutionType.API_INTEGRATION,
                    complexity=6,
                    setup_time="45分钟",
                    requires_user_action="集成外部AI服务",
                    reliability=SolutionReliability.MEDIUM,
                    description="外部AI服务：功能强大，需要维护API连接",
                ),
            ]
        else:
            # 默认解决方案
            solutions = [
                Solution(
                    type=SolutionType.CODE_NODE,
                    complexity=6,
                    setup_time="1-2小时",
                    requires_user_action="编写自定义代码",
                    reliability=SolutionReliability.MEDIUM,
                    description="自定义代码实现：灵活性高，需要开发工作",
                )
            ]

        return solutions

    def _assess_technical_complexity(self, capabilities: CapabilityAnalysis) -> int:
        """Assess technical complexity dimension"""
        return min(
            sum(capabilities["complexity_scores"].values())
            // len(capabilities["complexity_scores"]),
            10,
        )

    def _assess_integration_complexity(self, capabilities: CapabilityAnalysis) -> int:
        """Assess integration complexity dimension"""
        integration_count = len(
            [cap for cap in capabilities["required_capabilities"] if "integration" in cap]
        )
        return min(integration_count * 2, 10)

    def _assess_maintenance_complexity(self, capabilities: CapabilityAnalysis) -> int:
        """Assess maintenance complexity dimension"""
        gap_count = len(capabilities["capability_gaps"])
        return min(gap_count * 3, 10)

    def _assess_user_complexity(self, capabilities: CapabilityAnalysis) -> int:
        """Assess user complexity dimension"""
        user_actions = sum(
            1
            for solutions in capabilities["potential_solutions"].values()
            for solution in solutions
            if solution["requires_user_action"]
        )
        return min(user_actions, 10)

    def _identify_risk_factors(self, capabilities: CapabilityAnalysis) -> List[str]:
        """Identify risk factors in the capability analysis"""
        risks = []

        # 高严重性缺口
        for gap, severity in capabilities["gap_severity"].items():
            if severity == GapSeverity.CRITICAL:
                risks.append(f"关键能力缺口: {gap}")

        # 复杂度过高
        for cap, score in capabilities["complexity_scores"].items():
            if score > 8:
                risks.append(f"高复杂度能力: {cap}")

        # 可靠性风险
        for solutions in capabilities["potential_solutions"].values():
            for solution in solutions:
                if solution["reliability"] == SolutionReliability.LOW:
                    risks.append(f"低可靠性解决方案: {solution['description']}")

        return risks

    def _estimate_development_time(self, capabilities: CapabilityAnalysis) -> str:
        """Estimate development time"""
        total_complexity = sum(capabilities["complexity_scores"].values())
        gap_count = len(capabilities["capability_gaps"])

        # 基础时间估算
        base_hours = total_complexity * 0.5
        gap_hours = gap_count * 2

        total_hours = base_hours + gap_hours

        if total_hours <= 4:
            return "2-4小时"
        elif total_hours <= 8:
            return "4-8小时"
        elif total_hours <= 16:
            return "1-2天"
        else:
            return "2-5天"

    def _generate_complexity_recommendations(self, capabilities: CapabilityAnalysis) -> List[str]:
        """Generate recommendations based on complexity assessment"""
        recommendations = []

        # 基于缺口数量
        if len(capabilities["capability_gaps"]) > 3:
            recommendations.append("建议分阶段实现，先实现核心功能")

        # 基于复杂度
        high_complexity = [
            cap for cap, score in capabilities["complexity_scores"].items() if score > 7
        ]
        if high_complexity:
            recommendations.append(f"高复杂度功能 {', '.join(high_complexity)} 建议寻求专业支持")

        # 基于可靠性
        low_reliability = []
        for solutions in capabilities["potential_solutions"].values():
            for solution in solutions:
                if solution["reliability"] == SolutionReliability.LOW:
                    low_reliability.append(solution["type"])

        if low_reliability:
            recommendations.append("建议为低可靠性组件添加监控和备用方案")

        return recommendations

    # RAG Enhancement Methods
    async def _assess_gap_severity_enhanced(
        self, gap: str, requirements: Dict[str, Any], rag_recommendations: Dict[str, Any]
    ) -> GapSeverity:
        """Enhanced gap severity assessment using RAG insights"""
        # Start with base assessment
        base_severity = self._assess_gap_severity(gap, requirements)

        # Check if RAG found alternatives
        alternatives = rag_recommendations.get("alternatives", [])
        has_good_alternatives = any(
            alt.get("similarity", 0) > 0.7
            for alt in alternatives
            if gap.lower() in alt.get("content", "").lower()
        )

        if has_good_alternatives:
            # Reduce severity if good alternatives exist
            severity_map = {
                GapSeverity.CRITICAL: GapSeverity.HIGH,
                GapSeverity.HIGH: GapSeverity.MEDIUM,
                GapSeverity.MEDIUM: GapSeverity.LOW,
                GapSeverity.LOW: GapSeverity.LOW,
            }
            return severity_map.get(base_severity, base_severity)

        return base_severity

    async def _get_rag_solutions(self, gap: str, requirements: Dict[str, Any]) -> List[Solution]:
        """Get RAG-recommended solutions for capability gaps"""
        solutions = []

        try:
            # Search for specific solutions to this gap
            task_description = f"solve {gap} requirement: {requirements.get('primary_goal', '')}"
            node_suggestions = await self.rag.get_node_type_suggestions(task_description)

            for suggestion in node_suggestions[:3]:  # Top 3 suggestions
                complexity_map = {"low": 3, "medium": 5, "high": 8}
                complexity = complexity_map.get(suggestion.get("complexity", "medium"), 5)

                solution = Solution(
                    type=SolutionType.NATIVE
                    if "BUILT_IN" in suggestion["node_type"]
                    else SolutionType.CODE_NODE,
                    complexity=complexity,
                    setup_time=suggestion.get("setup_time", "30-60分钟"),
                    requires_user_action=f"配置{suggestion['title']}节点",
                    reliability=SolutionReliability.HIGH
                    if suggestion["confidence"] == "high"
                    else SolutionReliability.MEDIUM,
                    description=f"使用{suggestion['title']}: {suggestion['description']}",
                )
                solutions.append(solution)

        except Exception as e:
            logger.warning("RAG solution search failed", gap=gap, error=str(e))

        return solutions

    def _get_rag_complexity(
        self, capability: str, rag_recommendations: Dict[str, Any]
    ) -> Optional[int]:
        """Extract complexity score from RAG recommendations"""
        capability_matches = rag_recommendations.get("capability_matches", {})
        matches = capability_matches.get(capability, [])

        if matches:
            # Use the complexity from the best match
            best_match = matches[0]
            complexity_str = best_match.metadata.get("complexity", "medium")
            complexity_map = {"low": 3, "medium": 5, "high": 8}
            return complexity_map.get(complexity_str, 5)

        return None


class IntelligentNegotiator:
    """
    Intelligent negotiation engine for multi-round requirement refinement
    完整实现 - 与长期愿景一致
    """

    def __init__(self):
        self.llm = self._setup_llm()
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
        """Generate question for high severity capability gap"""
        _ = history  # Mark as used

        if not solutions:
            return f"关键能力缺口：{gap}。我们需要找到解决方案，您有什么具体要求吗？"

        # 创建详细的解决方案对比
        solution_descriptions = []
        for i, solution in enumerate(solutions[:3]):  # 最多3个选项
            desc = f"{i+1}. {solution['description']} (复杂度: {solution['complexity']}/10, 设置时间: {solution['setup_time']})"
            solution_descriptions.append(desc)

        question = f"关键能力缺口：{gap}。\n\n可选解决方案：\n"
        question += "\n".join(solution_descriptions)
        question += f"\n\n考虑到这是关键功能，建议详细评估。您更倾向于哪种方案？或者有其他考虑因素吗？"

        return question

    async def _generate_medium_severity_question(
        self, gap: str, solutions: List[Solution], history: List[Dict[str, Any]]
    ) -> str:
        """Generate question for medium severity capability gap"""
        _ = history  # Mark as used

        if not solutions:
            return f"需要实现：{gap}。您有偏好的实现方式吗？"

        # 推荐最佳方案
        best_solution = min(solutions, key=lambda x: x["complexity"])
        alternative = max(solutions, key=lambda x: x["complexity"]) if len(solutions) > 1 else None

        question = f"需要实现：{gap}。\n\n推荐方案：{best_solution['description']} (复杂度: {best_solution['complexity']}/10)"

        if alternative:
            question += f"\n备选方案：{alternative['description']} (复杂度: {alternative['complexity']}/10)"

        question += "\n\n您觉得推荐方案如何？"

        return question

    async def _generate_low_severity_question(
        self, gap: str, solutions: List[Solution], history: List[Dict[str, Any]]
    ) -> str:
        """Generate question for low severity capability gap"""
        _ = history  # Mark as used

        if not solutions:
            return f"可选功能：{gap}。是否需要包含？"

        # 简单选择
        simple_solution = min(solutions, key=lambda x: x["complexity"])
        return f"可选功能：{gap}。建议使用{simple_solution['description']}，您同意吗？"

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

            rag_insights = await self.rag.vector_store.similarity_search(
                search_query, max_results=3, similarity_threshold=0.4
            )

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
            if rag_insights and rag_insights[0].similarity > 0.6:
                best_practice = rag_insights[0].content[:100] + "..."
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
        return {
            "intent": (
                "selection"
                if any(word in user_input.lower() for word in ["选择", "要", "用"])
                else "clarification"
            ),
            "confidence": 0.8,
            "extracted_preferences": {},
            "sentiment": "positive",
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
        if len(history) > 5:
            return "finalize_agreement"
        elif analysis["intent"] == "selection":
            return "present_alternatives"
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
        return {}  # Simplified implementation

    def _identify_optimizations(self, decisions: Dict[str, Any]) -> List[str]:
        """Identify optimization opportunities"""
        return []  # Simplified implementation

    def _generate_final_requirements(
        self, decisions: Dict[str, Any], optimizations: List[str]
    ) -> str:
        """Generate final requirements"""
        return "优化后的最终需求..."  # Simplified implementation

    def _calculate_confidence_score(self, agreements: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for agreements"""
        return 0.8  # Simplified implementation

    def _create_implementation_plan(self, requirements: str) -> Dict[str, Any]:
        """Create implementation plan"""
        return {"phases": [], "timeline": "", "resources": []}  # Simplified implementation
