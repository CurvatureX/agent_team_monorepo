"""
Episodic Memory Implementation.

This implementation provides timestamped event storage and retrieval
using PostgreSQL with time-series optimization for temporal context.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from supabase import Client, create_client

from .base import MemoryBase

logger = logging.getLogger(__name__)


class EpisodicMemory(MemoryBase):
    """
    Episodic Memory for timestamped events and experiences.

    Features:
    - Temporal event storage with precise timestamps
    - Importance scoring for event significance
    - Time-based query and retrieval
    - Actor-Action-Object event modeling
    - Temporal pattern detection
    - Context-aware event relationships
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize episodic memory.

        Args:
            config: Configuration dict with keys:
                - supabase_url: Supabase project URL
                - supabase_key: Supabase service key
                - importance_threshold: Minimum importance for storage (default: 0.5)
                - retention_period: How long to keep events (default: "30 days")
                - temporal_context_window: Time window for retrieval (default: "7 days")
                - event_embedding: Generate embeddings for semantic search (default: False)
        """
        super().__init__(config)

        # Supabase configuration
        self.supabase_url = config.get("supabase_url")
        self.supabase_key = config.get("supabase_key")
        self.supabase: Optional[Client] = None

        # Episodic memory configuration
        self.importance_threshold = config.get("importance_threshold", 0.5)
        self.retention_period = config.get("retention_period", "30 days")
        self.temporal_context_window = config.get("temporal_context_window", "7 days")
        self.event_embedding = config.get("event_embedding", False)

        # Table names
        self.episodes_table = "episodic_memory"

    async def _setup(self) -> None:
        """Initialize Supabase client and ensure tables exist."""
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("supabase_url and supabase_key are required")

        try:
            self.supabase = create_client(self.supabase_url, self.supabase_key)

            # Test connection
            result = self.supabase.table(self.episodes_table).select("id").limit(1).execute()
            logger.info("EpisodicMemory connected to Supabase")

        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            raise

    def _parse_time_window(self, window: str) -> timedelta:
        """Parse time window string like '7 days' into timedelta."""
        try:
            parts = window.split()
            if len(parts) != 2:
                return timedelta(days=7)  # Default

            value, unit = parts
            value = int(value)

            if unit.startswith("day"):
                return timedelta(days=value)
            elif unit.startswith("hour"):
                return timedelta(hours=value)
            elif unit.startswith("minute"):
                return timedelta(minutes=value)
            elif unit.startswith("week"):
                return timedelta(weeks=value)
            else:
                return timedelta(days=value)

        except:
            return timedelta(days=7)  # Default fallback

    async def store(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store an episodic event.

        Args:
            data: Event data with keys:
                - actor: Who performed the action (required)
                - action: What action was performed (required)
                - object: What was acted upon (optional)
                - context: Additional context information (optional)
                - outcome: Result of the action (optional)
                - importance: Importance score 0.0-1.0 (optional, default: 0.5)
                - timestamp: Event timestamp (optional, default: now)
                - session_id: Session identifier (optional)
                - user_id: User identifier (optional)

        Returns:
            Dict with store operation results
        """
        try:
            actor = data.get("actor")
            action = data.get("action")

            if not actor or not action:
                return {"stored": False, "error": "actor and action are required"}

            # Extract event details
            event_object = data.get("object", {})
            context = data.get("context", {})
            outcome = data.get("outcome", {})
            importance = float(data.get("importance", 0.5))
            session_id = data.get("session_id")
            user_id = data.get("user_id")

            # Check importance threshold
            if importance < self.importance_threshold:
                return {
                    "stored": False,
                    "reason": f"Importance {importance} below threshold {self.importance_threshold}",
                }

            # Parse timestamp
            timestamp = data.get("timestamp")
            if timestamp:
                if isinstance(timestamp, str):
                    event_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                else:
                    event_time = timestamp
            else:
                event_time = datetime.utcnow()

            # Create episode ID
            episode_id = str(uuid.uuid4())

            # Create event description for search
            event_description = f"{actor} {action}"
            if isinstance(event_object, dict) and event_object:
                obj_desc = json.dumps(event_object) if event_object else ""
                event_description += f" {obj_desc}"
            elif isinstance(event_object, str):
                event_description += f" {event_object}"

            episode_data = {
                "id": episode_id,
                "actor": actor,
                "action": action,
                "object": json.dumps(event_object)
                if isinstance(event_object, dict)
                else str(event_object),
                "context": json.dumps(context) if isinstance(context, dict) else str(context),
                "outcome": json.dumps(outcome) if isinstance(outcome, dict) else str(outcome),
                "importance": importance,
                "timestamp": event_time.isoformat(),
                "session_id": session_id,
                "user_id": user_id,
                "event_description": event_description,
                "created_at": datetime.utcnow().isoformat(),
            }

            # Store episode
            result = self.supabase.table(self.episodes_table).insert(episode_data).execute()

            if result.data:
                return {
                    "stored": True,
                    "episode_id": episode_id,
                    "importance": importance,
                    "timestamp": event_time.isoformat(),
                    "actor": actor,
                    "action": action,
                }
            else:
                return {"stored": False, "error": "Failed to store episode"}

        except Exception as e:
            logger.error(f"Error storing episode: {e}")
            return {"stored": False, "error": str(e)}

    async def retrieve(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve episodic events based on query criteria.

        Args:
            query: Query parameters:
                - time_window: Time window to search (e.g., "7 days", "2 hours")
                - start_time: Start time for query (optional)
                - end_time: End time for query (optional)
                - actor: Filter by actor (optional)
                - action: Filter by action (optional)
                - session_id: Filter by session (optional)
                - user_id: Filter by user (optional)
                - min_importance: Minimum importance score (optional)
                - max_results: Maximum results (default: 50)
                - order_by: Order by 'timestamp' or 'importance' (default: 'timestamp')

        Returns:
            Dict with retrieved episodes
        """
        try:
            # Parse time parameters
            time_window = query.get("time_window", self.temporal_context_window)
            start_time = query.get("start_time")
            end_time = query.get("end_time")

            # If no explicit times, use time window
            if not start_time and not end_time:
                window_delta = self._parse_time_window(time_window)
                end_time = datetime.utcnow()
                start_time = end_time - window_delta
            elif start_time and not end_time:
                end_time = datetime.utcnow()
            elif end_time and not start_time:
                window_delta = self._parse_time_window(time_window)
                start_time = end_time - window_delta

            # Convert to ISO format if datetime objects
            if isinstance(start_time, datetime):
                start_time = start_time.isoformat()
            if isinstance(end_time, datetime):
                end_time = end_time.isoformat()

            # Other query parameters
            actor = query.get("actor")
            action = query.get("action")
            session_id = query.get("session_id")
            user_id = query.get("user_id")
            min_importance = query.get("min_importance", 0.0)
            max_results = query.get("max_results", 50)
            order_by = query.get("order_by", "timestamp")

            # Build Supabase query
            supabase_query = self.supabase.table(self.episodes_table).select("*")

            # Time range filter
            if start_time:
                supabase_query = supabase_query.gte("timestamp", start_time)
            if end_time:
                supabase_query = supabase_query.lte("timestamp", end_time)

            # Other filters
            if actor:
                supabase_query = supabase_query.eq("actor", actor)
            if action:
                supabase_query = supabase_query.eq("action", action)
            if session_id:
                supabase_query = supabase_query.eq("session_id", session_id)
            if user_id:
                supabase_query = supabase_query.eq("user_id", user_id)
            if min_importance > 0.0:
                supabase_query = supabase_query.gte("importance", min_importance)

            # Ordering
            if order_by == "importance":
                supabase_query = supabase_query.order("importance", desc=True)
            else:
                supabase_query = supabase_query.order("timestamp", desc=True)

            # Limit results
            supabase_query = supabase_query.limit(max_results)

            # Execute query
            result = supabase_query.execute()

            episodes = []
            for episode in result.data:
                # Parse JSON fields
                event_object = episode.get("object", "{}")
                context = episode.get("context", "{}")
                outcome = episode.get("outcome", "{}")

                try:
                    event_object = (
                        json.loads(event_object) if event_object and event_object != "None" else {}
                    )
                except:
                    pass

                try:
                    context = json.loads(context) if context and context != "None" else {}
                except:
                    pass

                try:
                    outcome = json.loads(outcome) if outcome and outcome != "None" else {}
                except:
                    pass

                episodes.append(
                    {
                        "episode_id": episode["id"],
                        "actor": episode["actor"],
                        "action": episode["action"],
                        "object": event_object,
                        "context": context,
                        "outcome": outcome,
                        "importance": episode["importance"],
                        "timestamp": episode["timestamp"],
                        "session_id": episode.get("session_id"),
                        "user_id": episode.get("user_id"),
                        "event_description": episode.get("event_description", ""),
                    }
                )

            return {
                "episodes": episodes,
                "total_count": len(episodes),
                "time_window": time_window,
                "start_time": start_time,
                "end_time": end_time,
            }

        except Exception as e:
            logger.error(f"Error retrieving episodes: {e}")
            return {"episodes": [], "error": str(e)}

    async def get_context(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get episodic context for LLM consumption.

        Args:
            query: Query parameters (same as retrieve)

        Returns:
            Dict with formatted episodic context for LLM
        """
        try:
            # Retrieve episodes
            result = await self.retrieve(query)

            if "error" in result:
                return {"episodes": [], "context_summary": "", "error": result["error"]}

            episodes = result["episodes"]

            if not episodes:
                return {
                    "episodes": [],
                    "context_summary": "No relevant episodic memories found.",
                    "temporal_patterns": {},
                    "metadata": {
                        "time_window": query.get("time_window", self.temporal_context_window),
                        "episode_count": 0,
                    },
                }

            # Analyze temporal patterns
            temporal_patterns = self._analyze_temporal_patterns(episodes)

            # Create context summary
            context_parts = []
            high_importance_episodes = [ep for ep in episodes if ep["importance"] >= 0.7]

            if high_importance_episodes:
                context_parts.append("## Recent Important Events:")
                for episode in high_importance_episodes[:5]:  # Top 5 important events
                    time_str = episode["timestamp"][:19]  # Remove microseconds
                    context_parts.append(
                        f"- [{time_str}] {episode['actor']} {episode['action']} "
                        f"(importance: {episode['importance']:.2f})"
                    )

                    if episode.get("outcome") and episode["outcome"]:
                        outcome_str = (
                            json.dumps(episode["outcome"])
                            if isinstance(episode["outcome"], dict)
                            else str(episode["outcome"])
                        )
                        context_parts.append(f"  → Result: {outcome_str}")

            # Recent activity summary
            recent_episodes = episodes[:10]  # Most recent 10
            if recent_episodes:
                context_parts.append("\n## Recent Activity:")
                for episode in recent_episodes:
                    time_str = episode["timestamp"][:19]
                    context_parts.append(f"- [{time_str}] {episode['event_description']}")

            # Temporal patterns
            if temporal_patterns:
                context_parts.append("\n## Patterns Detected:")
                for pattern_type, pattern_data in temporal_patterns.items():
                    if pattern_data:
                        context_parts.append(f"- {pattern_type}: {pattern_data}")

            context_summary = "\n".join(context_parts)

            # Estimate tokens
            estimated_tokens = len(context_summary) // 4

            return {
                "episodes": episodes,
                "context_summary": context_summary,
                "temporal_patterns": temporal_patterns,
                "estimated_tokens": estimated_tokens,
                "metadata": {
                    "time_window": query.get("time_window", self.temporal_context_window),
                    "episode_count": len(episodes),
                    "high_importance_count": len(high_importance_episodes),
                    "average_importance": sum(ep["importance"] for ep in episodes) / len(episodes),
                },
            }

        except Exception as e:
            logger.error(f"Error getting episodic context: {e}")
            return {"episodes": [], "context_summary": "", "error": str(e)}

    def _analyze_temporal_patterns(self, episodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze temporal patterns in episodes."""
        try:
            if not episodes:
                return {}

            patterns = {}

            # Most frequent actors
            actors = {}
            for episode in episodes:
                actor = episode["actor"]
                actors[actor] = actors.get(actor, 0) + 1

            if actors:
                most_frequent_actor = max(actors, key=actors.get)
                patterns[
                    "most_active_actor"
                ] = f"{most_frequent_actor} ({actors[most_frequent_actor]} events)"

            # Most frequent actions
            actions = {}
            for episode in episodes:
                action = episode["action"]
                actions[action] = actions.get(action, 0) + 1

            if actions:
                most_frequent_action = max(actions, key=actions.get)
                patterns[
                    "most_frequent_action"
                ] = f"{most_frequent_action} ({actions[most_frequent_action]} times)"

            # Success rate (if outcomes indicate success/failure)
            successful_outcomes = 0
            total_with_outcomes = 0

            for episode in episodes:
                outcome = episode.get("outcome")
                if outcome:
                    total_with_outcomes += 1
                    if isinstance(outcome, dict):
                        if outcome.get("success") or outcome.get("status") == "success":
                            successful_outcomes += 1
                    elif isinstance(outcome, str) and "success" in outcome.lower():
                        successful_outcomes += 1

            if total_with_outcomes > 0:
                success_rate = successful_outcomes / total_with_outcomes
                patterns[
                    "success_rate"
                ] = f"{success_rate:.1%} ({successful_outcomes}/{total_with_outcomes})"

            return patterns

        except Exception as e:
            logger.error(f"Error analyzing temporal patterns: {e}")
            return {}

    async def cleanup_old_episodes(self) -> Dict[str, Any]:
        """Clean up episodes older than retention period."""
        try:
            retention_delta = self._parse_time_window(self.retention_period)
            cutoff_time = datetime.utcnow() - retention_delta

            # Delete old episodes
            result = (
                self.supabase.table(self.episodes_table)
                .delete()
                .lt("timestamp", cutoff_time.isoformat())
                .execute()
            )

            deleted_count = len(result.data) if result.data else 0

            return {
                "cleaned_up": True,
                "deleted_count": deleted_count,
                "retention_period": self.retention_period,
                "cutoff_time": cutoff_time.isoformat(),
            }

        except Exception as e:
            logger.error(f"Error cleaning up old episodes: {e}")
            return {"cleaned_up": False, "error": str(e)}

    async def get_memory_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about episodic memory."""
        try:
            # Base query
            supabase_query = self.supabase.table(self.episodes_table).select("*")

            if user_id:
                supabase_query = supabase_query.eq("user_id", user_id)

            # Get all episodes for stats
            result = supabase_query.execute()
            episodes = result.data

            if not episodes:
                return {"total_episodes": 0, "user_id": user_id, "message": "No episodes found"}

            # Calculate statistics
            total_episodes = len(episodes)
            avg_importance = sum(ep["importance"] for ep in episodes) / total_episodes

            # Time range
            timestamps = [datetime.fromisoformat(ep["timestamp"]) for ep in episodes]
            earliest = min(timestamps)
            latest = max(timestamps)

            # Actor/Action breakdown
            actors = {}
            actions = {}
            for episode in episodes:
                actor = episode["actor"]
                action = episode["action"]
                actors[actor] = actors.get(actor, 0) + 1
                actions[action] = actions.get(action, 0) + 1

            return {
                "total_episodes": total_episodes,
                "average_importance": round(avg_importance, 3),
                "time_span": {
                    "earliest": earliest.isoformat(),
                    "latest": latest.isoformat(),
                    "duration_days": (latest - earliest).days,
                },
                "unique_actors": len(actors),
                "unique_actions": len(actions),
                "top_actors": dict(sorted(actors.items(), key=lambda x: x[1], reverse=True)[:5]),
                "top_actions": dict(sorted(actions.items(), key=lambda x: x[1], reverse=True)[:5]),
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting memory stats: {e}")
            return {"error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """Check the health of episodic memory connections."""
        try:
            # Test Supabase connection
            test_result = self.supabase.table(self.episodes_table).select("id").limit(1).execute()

            # Get basic stats
            count_result = (
                self.supabase.table(self.episodes_table).select("id", count="exact").execute()
            )
            episode_count = count_result.count if hasattr(count_result, "count") else 0

            return {
                "status": "healthy",
                "supabase_connected": True,
                "total_episodes": episode_count,
                "retention_period": self.retention_period,
                "importance_threshold": self.importance_threshold,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"EpisodicMemory health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
