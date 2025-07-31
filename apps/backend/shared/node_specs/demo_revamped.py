#!/usr/bin/env python3
"""
Demonstration of the Revamped Node Specification System v2.0

This demo showcases the revolutionary provider-based AI agents where functionality
is driven by system prompts rather than hardcoded roles.
"""

import os
import sys

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)


def demo_ai_agent_revolution():
    """Demonstrate the new AI agent approach."""
    print("🚀 Node Specification System v2.0 - AI Agent Revolution")
    print("=" * 65)

    try:
        from node_specs import __status__, __version__, node_spec_registry

        print(f"📦 Version: {__version__}")
        print(f"📋 Status: {__status__}")

        print("\n🤖 AI AGENT REVOLUTION: From Rigid Roles to Flexible Prompts")
        print("-" * 65)

        # Show the old vs new approach
        print("❌ OLD APPROACH: Hardcoded, Limited Roles")
        print("   • AI_AGENT_NODE.REPORT_GENERATOR")
        print("   • AI_AGENT_NODE.TASK_ANALYZER")
        print("   • AI_AGENT_NODE.DATA_INTEGRATOR")
        print("   • AI_AGENT_NODE.REMINDER_DECISION")
        print("   • Limited to predefined functions")
        print("   • Need new code for each new role")
        print("   • Difficult to customize behavior")

        print("\n✅ NEW APPROACH: Provider-Based, Prompt-Driven")
        print("   • AI_AGENT_NODE.GEMINI_NODE")
        print("   • AI_AGENT_NODE.OPENAI_NODE")
        print("   • AI_AGENT_NODE.CLAUDE_NODE")
        print("   • Unlimited functionality via system prompts")
        print("   • Easy customization and experimentation")
        print("   • Leverage provider-specific capabilities")

        # Demo different AI providers
        print("\n🎯 PROVIDER SHOWCASE")
        print("-" * 30)

        providers = ["GEMINI_NODE", "OPENAI_NODE", "CLAUDE_NODE"]

        for provider in providers:
            spec = node_spec_registry.get_spec("AI_AGENT_NODE", provider)
            if spec:
                print(f"\n🔹 {provider}")
                print(f"   Description: {spec.description}")

                # Show model versions
                model_param = spec.get_parameter("model_version")
                if model_param:
                    print(f"   Models: {', '.join(model_param.enum_values)}")

                # Show provider-specific parameters
                provider_specific = []
                for param in spec.parameters:
                    if param.name not in [
                        "system_prompt",
                        "temperature",
                        "max_tokens",
                        "top_p",
                        "response_format",
                        "timeout_seconds",
                        "retry_attempts",
                        "model_version",
                    ]:
                        provider_specific.append(param.name)

                if provider_specific:
                    print(f"   Unique features: {', '.join(provider_specific)}")

        print("\n📝 SYSTEM PROMPT EXAMPLES")
        print("-" * 30)

        examples = [
            {
                "title": "📊 Data Analysis Agent",
                "provider": "GEMINI_NODE",
                "prompt": """You are a senior data analyst with expertise in statistical analysis and business intelligence.

TASK: Analyze the provided dataset and deliver actionable insights.

ANALYSIS REQUIREMENTS:
1. Statistical Overview: Mean, median, standard deviation, quartiles
2. Trend Analysis: Identify patterns, seasonality, and anomalies
3. Correlation Analysis: Key relationships between variables
4. Business Insights: What do the patterns mean for business decisions?
5. Data Quality: Completeness, accuracy, potential issues
6. Recommendations: Specific, actionable next steps

OUTPUT FORMAT: Structured JSON with sections for each requirement above.
CONFIDENCE LEVELS: Include confidence scores (0-1) for each insight.""",
            },
            {
                "title": "🎯 Customer Service Router",
                "provider": "OPENAI_NODE",
                "prompt": """You are an intelligent customer service routing system.

TASK: Analyze customer inquiries and route to the appropriate department.

ROUTING RULES:
- "billing" → Payment issues, invoices, refunds, subscription problems
- "technical" → Product bugs, feature questions, integration help
- "sales" → New purchases, upgrades, pricing inquiries
- "general" → General questions, feedback, complaints

ANALYSIS PROCESS:
1. Extract key intent and entities from customer message
2. Consider urgency level (low/medium/high/critical)
3. Identify customer tier (basic/premium/enterprise)
4. Apply routing rules with confidence scoring

RESPONSE FORMAT:
{
  "department": "billing|technical|sales|general",
  "confidence": 0.95,
  "urgency": "low|medium|high|critical",
  "reasoning": "Brief explanation of routing decision",
  "suggested_response": "Recommended first response to customer"
}""",
            },
            {
                "title": "🔍 Code Security Auditor",
                "provider": "CLAUDE_NODE",
                "prompt": """You are a senior application security engineer conducting code reviews.

SECURITY FOCUS AREAS:
1. Input Validation: SQL injection, XSS, command injection vulnerabilities
2. Authentication/Authorization: Weak auth, privilege escalation, session issues
3. Data Protection: Sensitive data exposure, encryption weaknesses
4. Business Logic: Race conditions, workflow bypasses
5. Dependencies: Known vulnerabilities in libraries/packages
6. Configuration: Security misconfigurations, hardcoded secrets

ANALYSIS METHODOLOGY:
- Line-by-line security review
- OWASP Top 10 vulnerability assessment
- CWE (Common Weakness Enumeration) classification
- Risk scoring: Critical/High/Medium/Low
- Exploitability assessment

OUTPUT REQUIREMENTS:
- Specific line numbers for each finding
- Vulnerability type and CWE classification
- Risk level with CVSS-like scoring
- Proof of concept exploit (if applicable)
- Detailed remediation steps
- Code examples for secure alternatives

Be thorough but practical - focus on real security risks that could impact the application.""",
            },
        ]

        for i, example in enumerate(examples, 1):
            print(f"\n{example['title']}")
            print(f"Provider: {example['provider']}")
            print(f"System Prompt Preview:")

            # Show first few lines of the prompt
            lines = example["prompt"].strip().split("\n")[:8]
            for line in lines:
                print(f"   {line}")

            if len(example["prompt"].split("\n")) > 8:
                remaining = len(example["prompt"].split("\n")) - 8
                print(f"   ... ({remaining} more lines)")

        print("\n💡 BENEFITS OF THE NEW APPROACH")
        print("-" * 40)

        benefits = [
            "🎯 Unlimited Functionality: Any AI task possible through prompts",
            "🔧 Easy Customization: Just modify the system prompt",
            "🚀 Provider Optimization: Leverage unique capabilities of each AI",
            "📦 Simplified Codebase: Three providers instead of dozens of subtypes",
            "🧪 Rapid Experimentation: Test new AI behaviors instantly",
            "💰 Cost Optimization: Choose the right provider for each task",
            "🔍 Transparency: Clear understanding of what each node does",
            "🎨 Creative Freedom: Design custom AI behaviors for specific needs",
        ]

        for benefit in benefits:
            print(f"   {benefit}")

        print("\n🎉 MIGRATION EXAMPLE")
        print("-" * 25)

        print("OLD: Hardcoded Report Generator")
        print(
            """   {
     "type": "AI_AGENT_NODE",
     "subtype": "REPORT_GENERATOR",
     "parameters": {
       "report_type": "executive_summary",
       "target_audience": "stakeholder"
     }
   }"""
        )

        print("\nNEW: Flexible Claude Agent")
        print(
            """   {
     "type": "AI_AGENT_NODE",
     "subtype": "CLAUDE_NODE",
     "parameters": {
       "system_prompt": "You are an executive report generator...",
       "model_version": "claude-3-sonnet",
       "temperature": "0.3"
     }
   }"""
        )

        print("\n" + "=" * 65)
        print("🎊 The Future of AI Workflows is Here!")
        print("✨ Three providers, unlimited possibilities")
        print("🚀 Ready to revolutionize your AI workflows")

        return True

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = demo_ai_agent_revolution()
    sys.exit(0 if success else 1)
