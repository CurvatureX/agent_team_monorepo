#!/usr/bin/env python3
"""
Migration Script: Convert Slack Channel Names to Channel IDs

This script updates existing Slack triggers in the trigger_index table to convert
channel name filters like "hil", "general" to channel IDs like "C09D2JW6814".

Usage:
    python migrate_slack_channel_names.py [--dry-run] [--workflow-id WORKFLOW_ID]

Options:
    --dry-run: Show what would be changed without making actual updates
    --workflow-id: Only process a specific workflow ID
"""

import argparse
import asyncio
import json
import logging

# Add the parent directories to the path so we can import our modules
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import httpx

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.insert(0, backend_dir)

from workflow_scheduler.core.supabase_client import get_supabase_client

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SlackChannelMigration:
    """Handles migration of Slack channel names to channel IDs"""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.supabase = get_supabase_client()
        self.stats = {
            "total_triggers": 0,
            "triggers_needing_migration": 0,
            "successful_migrations": 0,
            "failed_migrations": 0,
            "skipped_triggers": 0,
        }

    async def run_migration(self, workflow_id: Optional[str] = None):
        """
        Run the complete migration process

        Args:
            workflow_id: Optional specific workflow to migrate
        """
        try:
            logger.info("🚀 Starting Slack channel name migration")
            if self.dry_run:
                logger.info("🔍 DRY RUN MODE - No actual changes will be made")

            # Get all Slack triggers
            triggers = await self.get_slack_triggers(workflow_id)
            self.stats["total_triggers"] = len(triggers)
            logger.info(f"📊 Found {len(triggers)} Slack triggers to examine")

            if not triggers:
                logger.info("✅ No Slack triggers found to migrate")
                return

            # Group triggers by user to batch OAuth token lookups
            triggers_by_user = await self.group_triggers_by_user(triggers)
            logger.info(f"👥 Processing triggers for {len(triggers_by_user)} users")

            # Process each user's triggers
            for user_id, user_triggers in triggers_by_user.items():
                await self.process_user_triggers(user_id, user_triggers)

            # Print final statistics
            self.print_migration_summary()

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}", exc_info=True)
            raise

    async def get_slack_triggers(self, workflow_id: Optional[str] = None) -> List[Dict]:
        """Get all Slack triggers from trigger_index table"""
        try:
            query = (
                self.supabase.table("trigger_index")
                .select("workflow_id, trigger_config, created_at, updated_at")
                .eq("trigger_type", "SLACK")
                .eq("deployment_status", "active")
            )

            if workflow_id:
                query = query.eq("workflow_id", workflow_id)

            response = query.execute()

            if not response.data:
                return []

            return response.data

        except Exception as e:
            logger.error(f"Error querying Slack triggers: {e}", exc_info=True)
            return []

    async def group_triggers_by_user(self, triggers: List[Dict]) -> Dict[str, List[Dict]]:
        """Group triggers by their workflow owner (user_id)"""
        triggers_by_user = {}

        for trigger in triggers:
            workflow_id = trigger["workflow_id"]

            # Get workflow owner
            try:
                workflow_response = (
                    self.supabase.table("workflows")
                    .select("user_id")
                    .eq("id", workflow_id)
                    .execute()
                )

                if workflow_response.data and len(workflow_response.data) > 0:
                    user_id = workflow_response.data[0].get("user_id")
                    if user_id:
                        if user_id not in triggers_by_user:
                            triggers_by_user[user_id] = []
                        triggers_by_user[user_id].append(trigger)
                    else:
                        logger.warning(f"No user_id found for workflow {workflow_id}")
                        self.stats["skipped_triggers"] += 1
                else:
                    logger.warning(f"Workflow {workflow_id} not found in database")
                    self.stats["skipped_triggers"] += 1

            except Exception as e:
                logger.error(f"Error getting workflow owner for {workflow_id}: {e}")
                self.stats["skipped_triggers"] += 1

        return triggers_by_user

    async def process_user_triggers(self, user_id: str, triggers: List[Dict]):
        """Process all triggers for a specific user"""
        logger.info(f"👤 Processing {len(triggers)} triggers for user {user_id}")

        # Get user's Slack OAuth token
        slack_token = await self.get_user_slack_token(user_id)
        if not slack_token:
            logger.warning(
                f"No Slack OAuth token found for user {user_id}, skipping {len(triggers)} triggers"
            )
            self.stats["skipped_triggers"] += len(triggers)
            return

        # Process each trigger for this user
        for trigger in triggers:
            await self.process_single_trigger(trigger, slack_token, user_id)

    async def get_user_slack_token(self, user_id: str) -> Optional[str]:
        """Get user's Slack OAuth token from database"""
        try:
            oauth_result = (
                self.supabase.table("oauth_tokens")
                .select("access_token")
                .eq("user_id", user_id)
                .eq("integration_id", "slack")
                .eq("is_active", True)
                .execute()
            )

            if oauth_result.data and len(oauth_result.data) > 0:
                return oauth_result.data[0].get("access_token")
            else:
                return None

        except Exception as e:
            logger.error(f"Error getting Slack token for user {user_id}: {e}")
            return None

    async def process_single_trigger(self, trigger: Dict, slack_token: str, user_id: str):
        """Process a single trigger to migrate its channel names"""
        workflow_id = trigger["workflow_id"]
        trigger_config = trigger["trigger_config"]

        try:
            # Check if this trigger needs migration
            channel_filter = trigger_config.get("channel_filter")
            if not channel_filter:
                logger.debug(f"Trigger {workflow_id} has no channel_filter, skipping")
                self.stats["skipped_triggers"] += 1
                return

            # Skip if already looks like channel IDs
            if self.is_already_channel_ids(channel_filter):
                logger.debug(f"Trigger {workflow_id} already has channel IDs: {channel_filter}")
                self.stats["skipped_triggers"] += 1
                return

            logger.info(f"🔄 Migrating trigger {workflow_id}: '{channel_filter}' → channel IDs")
            self.stats["triggers_needing_migration"] += 1

            # Resolve channel names to IDs
            resolved_ids = await self.resolve_channel_names_to_ids(channel_filter, slack_token)

            if resolved_ids and resolved_ids != channel_filter:
                # Update the trigger configuration
                updated_config = trigger_config.copy()
                updated_config["channel_filter"] = resolved_ids

                success = await self.update_trigger_config(workflow_id, updated_config)

                if success:
                    logger.info(
                        f"✅ Successfully migrated {workflow_id}: '{channel_filter}' → '{resolved_ids}'"
                    )
                    self.stats["successful_migrations"] += 1
                else:
                    logger.error(f"❌ Failed to update trigger {workflow_id} in database")
                    self.stats["failed_migrations"] += 1
            else:
                logger.warning(
                    f"⚠️ Could not resolve channels for {workflow_id}: '{channel_filter}'"
                )
                self.stats["failed_migrations"] += 1

        except Exception as e:
            logger.error(f"Error processing trigger {workflow_id}: {e}", exc_info=True)
            self.stats["failed_migrations"] += 1

    def is_already_channel_ids(self, channel_filter) -> bool:
        """Check if channel filter already contains channel IDs"""
        # Handle different data types
        if isinstance(channel_filter, list):
            # If it's a list, check if all items are channel IDs
            return all(isinstance(ch, str) and ch.startswith("C") for ch in channel_filter)
        elif isinstance(channel_filter, str):
            # Simple heuristic: if it starts with C and contains mostly uppercase letters/numbers
            if channel_filter.startswith("C"):
                return True

            # Check comma-separated values
            if "," in channel_filter:
                channels = [ch.strip() for ch in channel_filter.split(",")]
                return all(ch.startswith("C") for ch in channels)

        return False

    async def resolve_channel_names_to_ids(
        self, channel_filter: str, slack_token: str
    ) -> Optional[str]:
        """Resolve channel names to channel IDs using Slack API"""
        try:
            # Handle different channel filter formats
            if isinstance(channel_filter, list):
                # Already a list of channel names
                channel_names = [str(name).strip() for name in channel_filter]
            elif isinstance(channel_filter, str):
                # Handle comma-separated channel names
                if "," in channel_filter:
                    channel_names = [name.strip() for name in channel_filter.split(",")]
                else:
                    channel_names = [channel_filter.strip()]
            else:
                logger.warning(f"Unexpected channel_filter type: {type(channel_filter)}")
                return None

            resolved_ids = []

            async with httpx.AsyncClient(timeout=30.0) as client:
                for channel_name in channel_names:
                    channel_id = await self.find_channel_id_by_name(
                        client, slack_token, channel_name
                    )
                    if channel_id:
                        resolved_ids.append(channel_id)
                        logger.debug(f"Resolved '{channel_name}' → '{channel_id}'")
                    else:
                        logger.warning(f"Could not resolve channel '{channel_name}'")
                        # Keep original name as fallback
                        resolved_ids.append(channel_name)

            return ",".join(resolved_ids) if resolved_ids else None

        except Exception as e:
            logger.error(f"Error resolving channel names: {e}", exc_info=True)
            return None

    async def find_channel_id_by_name(
        self, client: httpx.AsyncClient, slack_token: str, channel_name: str
    ) -> Optional[str]:
        """Find channel ID by name using Slack API"""
        try:
            response = await client.get(
                "https://slack.com/api/conversations.list",
                headers={"Authorization": f"Bearer {slack_token}"},
                params={
                    "types": "public_channel",  # Only public channels for now since we don't have groups:read scope
                    "limit": 1000,
                },
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    channels = data.get("channels", [])
                    for channel in channels:
                        if channel.get("name") == channel_name:
                            return channel.get("id")
                else:
                    logger.warning(f"Slack API error for '{channel_name}': {data.get('error')}")
            else:
                logger.warning(f"HTTP error {response.status_code} for channel lookup")

            return None

        except Exception as e:
            logger.warning(f"Error finding channel '{channel_name}': {e}")
            return None

    async def update_trigger_config(self, workflow_id: str, updated_config: Dict) -> bool:
        """Update trigger configuration in database"""
        if self.dry_run:
            logger.info(
                f"[DRY RUN] Would update trigger {workflow_id} with config: {updated_config}"
            )
            return True

        try:
            response = (
                self.supabase.table("trigger_index")
                .update(
                    {"trigger_config": updated_config, "updated_at": datetime.utcnow().isoformat()}
                )
                .eq("workflow_id", workflow_id)
                .eq("trigger_type", "SLACK")
                .execute()
            )

            return bool(response.data)

        except Exception as e:
            logger.error(f"Error updating trigger config for {workflow_id}: {e}")
            return False

    def print_migration_summary(self):
        """Print summary of migration results"""
        logger.info("🏁 Migration completed!")
        logger.info("📊 Migration Summary:")
        logger.info(f"   📋 Total triggers examined: {self.stats['total_triggers']}")
        logger.info(f"   🔄 Triggers needing migration: {self.stats['triggers_needing_migration']}")
        logger.info(f"   ✅ Successful migrations: {self.stats['successful_migrations']}")
        logger.info(f"   ❌ Failed migrations: {self.stats['failed_migrations']}")
        logger.info(f"   ⏭️ Skipped triggers: {self.stats['skipped_triggers']}")

        if self.stats["failed_migrations"] > 0:
            logger.warning(
                f"⚠️ {self.stats['failed_migrations']} migrations failed - check logs above"
            )

        if self.dry_run:
            logger.info("🔍 DRY RUN completed - no actual changes were made")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Migrate Slack channel names to channel IDs")
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be changed without making updates"
    )
    parser.add_argument("--workflow-id", help="Only process a specific workflow ID")

    args = parser.parse_args()

    migration = SlackChannelMigration(dry_run=args.dry_run)
    await migration.run_migration(workflow_id=args.workflow_id)


if __name__ == "__main__":
    asyncio.run(main())
