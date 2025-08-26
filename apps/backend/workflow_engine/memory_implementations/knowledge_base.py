"""
Knowledge Base Memory Implementation.

This implementation provides structured knowledge storage and retrieval
using PostgreSQL for facts, rules, and domain knowledge with confidence scoring.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from supabase import Client, create_client

from .base import MemoryBase

logger = logging.getLogger(__name__)


class KnowledgeBaseMemory(MemoryBase):
    """
    Knowledge Base Memory for structured facts and rules.

    Features:
    - Structured fact storage with confidence scoring
    - Rule-based inference system
    - Domain-specific knowledge organization
    - Fact validation and conflict resolution
    - Relationship tracking between facts
    - Temporal fact versioning
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize knowledge base memory.

        Args:
            config: Configuration dict with keys:
                - supabase_url: Supabase project URL
                - supabase_key: Supabase service key
                - openai_api_key: OpenAI API key for fact extraction (optional)
                - confidence_threshold: Minimum confidence for fact storage (default: 0.8)
                - fact_validation: Enable fact validation against existing knowledge (default: True)
                - rule_inference: Enable rule-based inference (default: False)
                - domain_isolation: Enable domain-based fact isolation (default: True)
        """
        super().__init__(config)

        # Supabase configuration
        self.supabase_url = config.get("supabase_url")
        self.supabase_key = config.get("supabase_key")
        self.supabase: Optional[Client] = None

        # OpenAI configuration (optional for fact extraction)
        self.openai_api_key = config.get("openai_api_key")

        # Knowledge base configuration
        self.confidence_threshold = config.get("confidence_threshold", 0.8)
        self.fact_validation = config.get("fact_validation", True)
        self.rule_inference = config.get("rule_inference", False)
        self.domain_isolation = config.get("domain_isolation", True)

        # Table names
        self.facts_table = "knowledge_facts"
        self.rules_table = "knowledge_rules"
        self.fact_relationships_table = "fact_relationships"

    async def _setup(self) -> None:
        """Initialize Supabase client and ensure tables exist."""
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("supabase_url and supabase_key are required")

        try:
            self.supabase = create_client(self.supabase_url, self.supabase_key)

            # Test connection
            result = self.supabase.table(self.facts_table).select("id").limit(1).execute()
            logger.info("KnowledgeBaseMemory connected to Supabase")

        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            raise

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store knowledge facts or rules.

        Args:
            data: Knowledge data with keys:
                - content: Text content for fact extraction (optional if facts provided)
                - facts: List of structured facts (optional)
                - rules: List of rules (optional)
                - domain: Domain/category for the knowledge (default: 'general')
                - confidence: Confidence score 0.0-1.0 (default: 0.8)
                - user_id: User identifier (optional)
                - source: Knowledge source (optional)
                - extract_facts: Whether to auto-extract facts from content (default: True)

        Returns:
            Dict with store operation results
        """
        try:
            content = data.get("content", "")
            provided_facts = data.get("facts", [])
            provided_rules = data.get("rules", [])
            domain = data.get("domain", "general")
            confidence = float(data.get("confidence", 0.8))
            user_id = data.get("user_id")
            source = data.get("source", "user_input")
            extract_facts = data.get("extract_facts", True)

            results = {
                "stored": True,
                "facts_stored": 0,
                "rules_stored": 0,
                "facts_updated": 0,
                "conflicts_detected": 0,
                "inferences_made": 0,
            }

            # Auto-extract facts from content if enabled and content provided
            extracted_facts = []
            if extract_facts and content and self.openai_api_key:
                extracted_facts = await self._extract_facts_from_content(content, domain)
                logger.info(f"Extracted {len(extracted_facts)} facts from content")

            # Combine provided and extracted facts
            all_facts = provided_facts + extracted_facts

            # Store facts
            if all_facts:
                fact_results = await self._store_facts(
                    all_facts, domain, confidence, user_id, source
                )
                results.update(fact_results)

            # Store rules
            if provided_rules:
                rule_results = await self._store_rules(
                    provided_rules, domain, confidence, user_id, source
                )
                results["rules_stored"] = rule_results["rules_stored"]

            # Apply rule inference if enabled
            if self.rule_inference and all_facts:
                inference_results = await self._apply_rule_inference(all_facts, domain)
                results["inferences_made"] = inference_results.get("inferences_made", 0)

            results["timestamp"] = datetime.utcnow().isoformat()
            return results

        except Exception as e:
            logger.error(f"Error storing knowledge: {e}")
            return {"stored": False, "error": str(e)}

    async def _extract_facts_from_content(self, content: str, domain: str) -> List[Dict[str, Any]]:
        """Extract structured facts from text content using OpenAI."""
        if not self.openai_api_key:
            return []

        try:
            import openai

            client = openai.AsyncOpenAI(api_key=self.openai_api_key)

            extraction_prompt = f"""
Extract structured facts from the following text. Return JSON array of facts.
Each fact should have: subject, predicate, object, confidence (0.0-1.0), fact_type.

Domain: {domain}
Text: {content}

Return ONLY the JSON array, no other text:
"""

            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a fact extraction expert. Return only valid JSON.",
                    },
                    {"role": "user", "content": extraction_prompt},
                ],
                temperature=0.1,
                max_tokens=1000,
            )

            result_text = response.choices[0].message.content.strip()

            # Parse JSON response
            facts = json.loads(result_text)

            # Validate fact structure
            validated_facts = []
            for fact in facts:
                if isinstance(fact, dict) and all(
                    key in fact for key in ["subject", "predicate", "object"]
                ):
                    validated_facts.append(
                        {
                            "subject": str(fact["subject"]),
                            "predicate": str(fact["predicate"]),
                            "object": str(fact["object"]),
                            "confidence": float(fact.get("confidence", 0.7)),
                            "fact_type": fact.get("fact_type", "extracted"),
                            "source_text": content[:200] + "..." if len(content) > 200 else content,
                        }
                    )

            return validated_facts

        except Exception as e:
            logger.error(f"Error extracting facts: {e}")
            return []

    async def _store_facts(
        self,
        facts: List[Dict[str, Any]],
        domain: str,
        default_confidence: float,
        user_id: Optional[str],
        source: str,
    ) -> Dict[str, Any]:
        """Store facts in the knowledge base with validation."""
        results = {"facts_stored": 0, "facts_updated": 0, "conflicts_detected": 0}

        for fact in facts:
            try:
                # Validate fact structure
                if not all(key in fact for key in ["subject", "predicate", "object"]):
                    logger.warning(f"Invalid fact structure: {fact}")
                    continue

                subject = str(fact["subject"]).strip()
                predicate = str(fact["predicate"]).strip()
                object_value = str(fact["object"]).strip()
                confidence = float(fact.get("confidence", default_confidence))
                fact_type = fact.get("fact_type", "user_provided")

                # Skip facts below confidence threshold
                if confidence < self.confidence_threshold:
                    continue

                # Check for existing conflicting facts if validation enabled
                conflicts = []
                if self.fact_validation:
                    conflicts = await self._detect_fact_conflicts(
                        subject, predicate, object_value, domain
                    )

                    if conflicts:
                        results["conflicts_detected"] += len(conflicts)
                        logger.info(
                            f"Detected {len(conflicts)} conflicts for fact: {subject} {predicate} {object_value}"
                        )

                # Create fact ID
                fact_id = str(uuid.uuid4())

                fact_data = {
                    "id": fact_id,
                    "subject": subject,
                    "predicate": predicate,
                    "object": object_value,
                    "fact_type": fact_type,
                    "domain": domain,
                    "confidence": confidence,
                    "user_id": user_id,
                    "source": source,
                    "source_text": fact.get("source_text", ""),
                    "metadata": json.dumps(fact.get("metadata", {})),
                    "is_active": True,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }

                # Check if identical fact exists
                existing = (
                    self.supabase.table(self.facts_table)
                    .select("id,confidence")
                    .eq("subject", subject)
                    .eq("predicate", predicate)
                    .eq("object", object_value)
                    .eq("domain", domain)
                    .eq("is_active", True)
                    .execute()
                )

                if existing.data:
                    # Update existing fact if new confidence is higher
                    existing_fact = existing.data[0]
                    if confidence > existing_fact["confidence"]:
                        update_result = (
                            self.supabase.table(self.facts_table)
                            .update(
                                {
                                    "confidence": confidence,
                                    "source": source,
                                    "updated_at": datetime.utcnow().isoformat(),
                                    "metadata": fact_data["metadata"],
                                }
                            )
                            .eq("id", existing_fact["id"])
                            .execute()
                        )

                        if update_result.data:
                            results["facts_updated"] += 1
                else:
                    # Insert new fact
                    insert_result = (
                        self.supabase.table(self.facts_table).insert(fact_data).execute()
                    )

                    if insert_result.data:
                        results["facts_stored"] += 1

            except Exception as e:
                logger.error(f"Error storing individual fact: {e}")
                continue

        return results

    async def _detect_fact_conflicts(
        self, subject: str, predicate: str, object_value: str, domain: str
    ) -> List[Dict[str, Any]]:
        """Detect conflicting facts in the knowledge base."""
        try:
            # Look for facts with same subject and predicate but different object
            conflicts = (
                self.supabase.table(self.facts_table)
                .select("*")
                .eq("subject", subject)
                .eq("predicate", predicate)
                .neq("object", object_value)
                .eq("domain", domain)
                .eq("is_active", True)
                .execute()
            )

            return conflicts.data or []

        except Exception as e:
            logger.error(f"Error detecting conflicts: {e}")
            return []

    async def _store_rules(
        self,
        rules: List[Dict[str, Any]],
        domain: str,
        confidence: float,
        user_id: Optional[str],
        source: str,
    ) -> Dict[str, Any]:
        """Store inference rules."""
        results = {"rules_stored": 0}

        for rule in rules:
            try:
                if not all(key in rule for key in ["condition", "conclusion"]):
                    continue

                rule_id = str(uuid.uuid4())
                rule_data = {
                    "id": rule_id,
                    "name": rule.get("name", f"rule_{rule_id[:8]}"),
                    "condition": json.dumps(rule["condition"]),
                    "conclusion": json.dumps(rule["conclusion"]),
                    "domain": domain,
                    "confidence": confidence,
                    "user_id": user_id,
                    "source": source,
                    "is_active": True,
                    "created_at": datetime.utcnow().isoformat(),
                }

                insert_result = self.supabase.table(self.rules_table).insert(rule_data).execute()

                if insert_result.data:
                    results["rules_stored"] += 1

            except Exception as e:
                logger.error(f"Error storing rule: {e}")
                continue

        return results

    async def _apply_rule_inference(
        self, facts: List[Dict[str, Any]], domain: str
    ) -> Dict[str, Any]:
        """Apply rule-based inference to derive new facts."""
        results = {"inferences_made": 0}

        try:
            # Get active rules for domain
            rules_result = (
                self.supabase.table(self.rules_table)
                .select("*")
                .eq("domain", domain)
                .eq("is_active", True)
                .execute()
            )

            if not rules_result.data:
                return results

            # Simple rule inference (can be expanded)
            for rule in rules_result.data:
                try:
                    condition = json.loads(rule["condition"])
                    conclusion = json.loads(rule["conclusion"])

                    # Check if condition matches any facts
                    if self._check_rule_condition(condition, facts):
                        # Create new inferred fact
                        inferred_fact = {
                            "subject": conclusion.get("subject", ""),
                            "predicate": conclusion.get("predicate", ""),
                            "object": conclusion.get("object", ""),
                            "fact_type": "inferred",
                            "confidence": min(
                                rule["confidence"] * 0.9, 1.0
                            ),  # Slightly lower confidence for inferred facts
                            "metadata": {"inferred_by_rule": rule["id"]},
                        }

                        # Store inferred fact
                        inference_results = await self._store_facts(
                            [inferred_fact],
                            domain,
                            inferred_fact["confidence"],
                            rule.get("user_id"),
                            f"inference_{rule['id']}",
                        )

                        results["inferences_made"] += inference_results.get("facts_stored", 0)

                except Exception as e:
                    logger.error(f"Error applying rule {rule['id']}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in rule inference: {e}")

        return results

    def _check_rule_condition(self, condition: Dict[str, Any], facts: List[Dict[str, Any]]) -> bool:
        """Check if rule condition is satisfied by given facts."""
        try:
            # Simple pattern matching (can be expanded for complex conditions)
            required_pattern = condition.get("pattern", {})

            for fact in facts:
                if all(
                    fact.get(key) == value
                    for key, value in required_pattern.items()
                    if key in ["subject", "predicate", "object"]
                ):
                    return True

            return False

        except Exception:
            return False

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve knowledge facts and rules.

        Args:
            query: Query parameters:
                - domain: Domain to search (optional)
                - subject: Subject to search for (optional)
                - predicate: Predicate to search for (optional)
                - object: Object to search for (optional)
                - fact_type: Type of facts to retrieve (optional)
                - min_confidence: Minimum confidence score (optional)
                - max_results: Maximum results (default: 50)
                - include_rules: Include rules in results (default: False)
                - user_id: User ID filter (optional)

        Returns:
            Dict with retrieved knowledge
        """
        try:
            domain = query.get("domain")
            subject = query.get("subject")
            predicate = query.get("predicate")
            object_value = query.get("object")
            fact_type = query.get("fact_type")
            min_confidence = query.get("min_confidence", 0.0)
            max_results = query.get("max_results", 50)
            include_rules = query.get("include_rules", False)
            user_id = query.get("user_id")

            # Build facts query
            facts_query = self.supabase.table(self.facts_table).select("*").eq("is_active", True)

            if domain:
                facts_query = facts_query.eq("domain", domain)
            if subject:
                facts_query = facts_query.eq("subject", subject)
            if predicate:
                facts_query = facts_query.eq("predicate", predicate)
            if object_value:
                facts_query = facts_query.eq("object", object_value)
            if fact_type:
                facts_query = facts_query.eq("fact_type", fact_type)
            if min_confidence > 0.0:
                facts_query = facts_query.gte("confidence", min_confidence)
            if user_id:
                facts_query = facts_query.eq("user_id", user_id)

            # Order by confidence and limit
            facts_query = facts_query.order("confidence", desc=True).limit(max_results)

            # Execute facts query
            facts_result = facts_query.execute()

            facts = []
            for fact in facts_result.data:
                metadata = fact.get("metadata", "{}")
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}

                facts.append(
                    {
                        "fact_id": fact["id"],
                        "subject": fact["subject"],
                        "predicate": fact["predicate"],
                        "object": fact["object"],
                        "fact_type": fact["fact_type"],
                        "domain": fact["domain"],
                        "confidence": fact["confidence"],
                        "source": fact.get("source", ""),
                        "source_text": fact.get("source_text", ""),
                        "metadata": metadata,
                        "created_at": fact["created_at"],
                        "updated_at": fact["updated_at"],
                    }
                )

            result = {"facts": facts, "total_facts": len(facts), "rules": []}

            # Include rules if requested
            if include_rules:
                rules_query = (
                    self.supabase.table(self.rules_table).select("*").eq("is_active", True)
                )

                if domain:
                    rules_query = rules_query.eq("domain", domain)
                if user_id:
                    rules_query = rules_query.eq("user_id", user_id)

                rules_result = rules_query.execute()

                rules = []
                for rule in rules_result.data:
                    condition = rule.get("condition", "{}")
                    conclusion = rule.get("conclusion", "{}")

                    try:
                        condition = (
                            json.loads(condition) if isinstance(condition, str) else condition
                        )
                        conclusion = (
                            json.loads(conclusion) if isinstance(conclusion, str) else conclusion
                        )
                    except:
                        condition = {}
                        conclusion = {}

                    rules.append(
                        {
                            "rule_id": rule["id"],
                            "name": rule["name"],
                            "condition": condition,
                            "conclusion": conclusion,
                            "domain": rule["domain"],
                            "confidence": rule["confidence"],
                            "created_at": rule["created_at"],
                        }
                    )

                result["rules"] = rules
                result["total_rules"] = len(rules)

            return result

        except Exception as e:
            logger.error(f"Error retrieving knowledge: {e}")
            return {"facts": [], "rules": [], "error": str(e)}

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get knowledge context for LLM consumption.

        Args:
            query: Query parameters (same as retrieve)

        Returns:
            Dict with formatted knowledge context for LLM
        """
        try:
            # Retrieve knowledge
            result = await self.retrieve(query)

            if "error" in result:
                return {"facts": [], "knowledge_summary": "", "error": result["error"]}

            facts = result["facts"]
            rules = result.get("rules", [])

            if not facts and not rules:
                return {
                    "facts": [],
                    "knowledge_summary": "No relevant knowledge found.",
                    "rules": [],
                    "inferences": [],
                    "metadata": {
                        "domain": query.get("domain", "general"),
                        "fact_count": 0,
                        "rule_count": 0,
                    },
                }

            # Format knowledge for LLM
            context_parts = []

            # Organize facts by domain and confidence
            if facts:
                context_parts.append("## Knowledge Facts:")

                # Group by domain
                facts_by_domain = {}
                for fact in facts:
                    domain = fact["domain"]
                    if domain not in facts_by_domain:
                        facts_by_domain[domain] = []
                    facts_by_domain[domain].append(fact)

                for domain, domain_facts in facts_by_domain.items():
                    if len(facts_by_domain) > 1:
                        context_parts.append(f"\n### {domain.title()} Domain:")

                    # Show high confidence facts first
                    high_confidence_facts = [f for f in domain_facts if f["confidence"] >= 0.9]
                    medium_confidence_facts = [
                        f for f in domain_facts if 0.7 <= f["confidence"] < 0.9
                    ]

                    if high_confidence_facts:
                        for fact in high_confidence_facts[:5]:  # Top 5 high confidence
                            context_parts.append(
                                f"- {fact['subject']} {fact['predicate']} {fact['object']} (confidence: {fact['confidence']:.2f})"
                            )

                    if medium_confidence_facts and len(high_confidence_facts) < 5:
                        remaining_slots = 5 - len(high_confidence_facts)
                        for fact in medium_confidence_facts[:remaining_slots]:
                            context_parts.append(
                                f"- {fact['subject']} {fact['predicate']} {fact['object']} (confidence: {fact['confidence']:.2f})"
                            )

            # Include rules if available
            if rules:
                context_parts.append("\n## Knowledge Rules:")
                for rule in rules[:3]:  # Top 3 rules
                    context_parts.append(
                        f"- {rule['name']}: IF {rule['condition']} THEN {rule['conclusion']}"
                    )

            knowledge_summary = "\n".join(context_parts)

            # Calculate statistics
            avg_confidence = sum(f["confidence"] for f in facts) / len(facts) if facts else 0.0
            domains = list(set(f["domain"] for f in facts))

            # Estimate tokens
            estimated_tokens = len(knowledge_summary) // 4

            return {
                "facts": facts,
                "knowledge_summary": knowledge_summary,
                "rules": rules,
                "inferences": [],  # Would be populated by rule engine
                "estimated_tokens": estimated_tokens,
                "metadata": {
                    "domains": domains,
                    "fact_count": len(facts),
                    "rule_count": len(rules),
                    "average_confidence": round(avg_confidence, 3),
                    "confidence_distribution": {
                        "high": len([f for f in facts if f["confidence"] >= 0.9]),
                        "medium": len([f for f in facts if 0.7 <= f["confidence"] < 0.9]),
                        "low": len([f for f in facts if f["confidence"] < 0.7]),
                    },
                },
            }

        except Exception as e:
            logger.error(f"Error getting knowledge context: {e}")
            return {"facts": [], "knowledge_summary": "", "error": str(e)}

    async def query_knowledge(
        self, natural_query: str, domain: Optional[str] = None
    ) -> Dict[str, Any]:
        """Query knowledge base with natural language."""
        try:
            # Simple keyword-based search (can be enhanced with NLP)
            keywords = natural_query.lower().split()

            # Search facts containing keywords
            matching_facts = []

            for keyword in keywords:
                # Search in subject, predicate, object fields
                subject_matches = (
                    self.supabase.table(self.facts_table)
                    .select("*")
                    .ilike("subject", f"%{keyword}%")
                    .eq("is_active", True)
                    .limit(10)
                    .execute()
                )
                predicate_matches = (
                    self.supabase.table(self.facts_table)
                    .select("*")
                    .ilike("predicate", f"%{keyword}%")
                    .eq("is_active", True)
                    .limit(10)
                    .execute()
                )
                object_matches = (
                    self.supabase.table(self.facts_table)
                    .select("*")
                    .ilike("object", f"%{keyword}%")
                    .eq("is_active", True)
                    .limit(10)
                    .execute()
                )

                matching_facts.extend(subject_matches.data or [])
                matching_facts.extend(predicate_matches.data or [])
                matching_facts.extend(object_matches.data or [])

            # Remove duplicates and filter by domain
            unique_facts = {}
            for fact in matching_facts:
                if domain and fact["domain"] != domain:
                    continue
                unique_facts[fact["id"]] = fact

            # Sort by confidence
            sorted_facts = sorted(
                unique_facts.values(), key=lambda x: x["confidence"], reverse=True
            )

            return await self.get_context(
                {"facts": sorted_facts[:10], "domain": domain}  # Top 10 matches
            )

        except Exception as e:
            logger.error(f"Error querying knowledge: {e}")
            return {"facts": [], "knowledge_summary": "", "error": str(e)}

    async def get_domain_stats(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about knowledge in a domain."""
        try:
            base_query = self.supabase.table(self.facts_table).select("*").eq("is_active", True)

            if domain:
                base_query = base_query.eq("domain", domain)

            facts_result = base_query.execute()
            facts = facts_result.data or []

            if not facts:
                return {"domain": domain, "total_facts": 0, "message": "No facts found"}

            # Calculate statistics
            total_facts = len(facts)
            avg_confidence = sum(f["confidence"] for f in facts) / total_facts

            # Group by fact types
            fact_types = {}
            subjects = {}
            predicates = {}

            for fact in facts:
                # Fact types
                fact_type = fact["fact_type"]
                fact_types[fact_type] = fact_types.get(fact_type, 0) + 1

                # Subjects
                subject = fact["subject"]
                subjects[subject] = subjects.get(subject, 0) + 1

                # Predicates
                predicate = fact["predicate"]
                predicates[predicate] = predicates.get(predicate, 0) + 1

            return {
                "domain": domain,
                "total_facts": total_facts,
                "average_confidence": round(avg_confidence, 3),
                "fact_types": dict(
                    sorted(fact_types.items(), key=lambda x: x[1], reverse=True)[:5]
                ),
                "top_subjects": dict(
                    sorted(subjects.items(), key=lambda x: x[1], reverse=True)[:5]
                ),
                "top_predicates": dict(
                    sorted(predicates.items(), key=lambda x: x[1], reverse=True)[:5]
                ),
                "confidence_distribution": {
                    "high (≥0.9)": len([f for f in facts if f["confidence"] >= 0.9]),
                    "medium (0.7-0.9)": len([f for f in facts if 0.7 <= f["confidence"] < 0.9]),
                    "low (<0.7)": len([f for f in facts if f["confidence"] < 0.7]),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting domain stats: {e}")
            return {"error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of knowledge base connections."""
        try:
            # Test Supabase connection
            facts_test = self.supabase.table(self.facts_table).select("id").limit(1).execute()
            rules_test = self.supabase.table(self.rules_table).select("id").limit(1).execute()

            # Get basic stats
            facts_count = (
                self.supabase.table(self.facts_table)
                .select("id", count="exact")
                .eq("is_active", True)
                .execute()
            )
            rules_count = (
                self.supabase.table(self.rules_table)
                .select("id", count="exact")
                .eq("is_active", True)
                .execute()
            )

            total_facts = facts_count.count if hasattr(facts_count, "count") else 0
            total_rules = rules_count.count if hasattr(rules_count, "count") else 0

            return {
                "status": "healthy",
                "supabase_connected": True,
                "total_facts": total_facts,
                "total_rules": total_rules,
                "confidence_threshold": self.confidence_threshold,
                "fact_validation_enabled": self.fact_validation,
                "rule_inference_enabled": self.rule_inference,
                "openai_available": bool(self.openai_api_key),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"KnowledgeBase health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
