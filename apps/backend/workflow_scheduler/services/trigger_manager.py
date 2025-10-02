import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from shared.models.execution_new import ExecutionStatus
from shared.models.node_enums import TriggerSubtype
from shared.models.trigger import TriggerSpec, TriggerStatus
from shared.models.workflow_new import WorkflowExecutionResponse
from workflow_scheduler.services.event_router import EventRouter
from workflow_scheduler.services.lock_manager import DistributedLockManager
from workflow_scheduler.services.notification_service import NotificationService
from workflow_scheduler.triggers.base import BaseTrigger

logger = logging.getLogger(__name__)


class TriggerManager:
    """Central manager for all trigger types and their lifecycle"""

    def __init__(self, lock_manager: DistributedLockManager, direct_db_service=None):
        self.lock_manager = lock_manager
        self.event_router = EventRouter()
        self.notification_service = NotificationService()
        self.direct_db_service = direct_db_service
        self._triggers: Dict[str, List[BaseTrigger]] = {}  # workflow_id -> list of triggers
        self._trigger_registry: Dict[TriggerSubtype, type] = {}

    def register_trigger_class(self, trigger_type: TriggerSubtype, trigger_class: type) -> None:
        """Register a trigger class for a specific trigger type"""
        self._trigger_registry[trigger_type] = trigger_class
        logger.info(f"Registered trigger class for type: {trigger_type.value}")

    async def restore_active_triggers(self) -> Dict[str, Any]:
        """
        Restore all active triggers from the trigger_index table on startup

        Returns:
            Dict with restoration statistics
        """
        if not self.direct_db_service:
            logger.error("Cannot restore triggers: direct_db_service not available")
            return {"success": False, "error": "No database service"}

        try:
            logger.info("🔄 Restoring active triggers from trigger_index...")

            # Query trigger_index for all active triggers using direct connection
            query = """
                SELECT workflow_id, trigger_type, trigger_subtype, trigger_config, index_key
                FROM trigger_index
                WHERE deployment_status = 'active'
                ORDER BY workflow_id, trigger_subtype
            """

            # Execute query using the connection pool
            conn_context = await self.direct_db_service._get_connection()
            async with conn_context as connection:
                rows = await connection.fetch(query)

            if not rows:
                logger.info("No active triggers found in trigger_index")
                return {"success": True, "restored_count": 0, "workflows": []}

            # Group triggers by workflow_id
            workflows_triggers = {}
            for row in rows:
                workflow_id = row["workflow_id"]
                trigger_subtype_str = row["trigger_subtype"]
                trigger_config_raw = row["trigger_config"]

                # Parse trigger_config if it's a string
                if isinstance(trigger_config_raw, str):
                    try:
                        trigger_config = json.loads(trigger_config_raw)
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse trigger_config for workflow {workflow_id}, skipping"
                        )
                        continue
                else:
                    trigger_config = trigger_config_raw

                if workflow_id not in workflows_triggers:
                    workflows_triggers[workflow_id] = []

                # Convert trigger_subtype string to enum
                try:
                    trigger_subtype = TriggerSubtype(trigger_subtype_str)
                except ValueError:
                    logger.warning(f"Unknown trigger subtype: {trigger_subtype_str}, skipping")
                    continue

                # Create TriggerSpec
                spec = TriggerSpec(
                    type="TRIGGER",
                    subtype=trigger_subtype,
                    enabled=trigger_config.get("enabled", True),
                    parameters=trigger_config,
                )

                workflows_triggers[workflow_id].append(spec)

            # Register triggers for each workflow
            restored_count = 0
            failed_count = 0
            restored_workflows = []

            for workflow_id, trigger_specs in workflows_triggers.items():
                logger.info(f"Restoring {len(trigger_specs)} triggers for workflow {workflow_id}")
                success = await self.register_triggers(workflow_id, trigger_specs)

                if success:
                    restored_count += len(trigger_specs)
                    restored_workflows.append(workflow_id)
                    logger.info(f"✅ Restored triggers for workflow {workflow_id}")
                else:
                    failed_count += len(trigger_specs)
                    logger.error(f"❌ Failed to restore triggers for workflow {workflow_id}")

            logger.info(
                f"✅ Trigger restoration complete: {restored_count} triggers restored, "
                f"{failed_count} failed across {len(restored_workflows)} workflows"
            )

            return {
                "success": True,
                "restored_count": restored_count,
                "failed_count": failed_count,
                "workflows": restored_workflows,
                "total_workflows": len(workflows_triggers),
            }

        except Exception as e:
            logger.error(f"❌ Failed to restore active triggers: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def register_triggers(self, workflow_id: str, trigger_specs: List[TriggerSpec]) -> bool:
        """
        Register and start triggers for a workflow

        Args:
            workflow_id: Workflow identifier
            trigger_specs: List of trigger specifications

        Returns:
            bool: True if all triggers registered successfully
        """
        try:
            logger.info(f"Registering {len(trigger_specs)} triggers for workflow {workflow_id}")

            # Clean up existing triggers first
            await self.unregister_triggers(workflow_id)

            triggers = []

            for spec in trigger_specs:
                trigger = await self._create_trigger(workflow_id, spec)
                if trigger:
                    triggers.append(trigger)
                else:
                    logger.error(
                        f"Failed to create trigger of type {spec.subtype} for workflow {workflow_id}"
                    )
                    # Cleanup already created triggers
                    for t in triggers:
                        await t.stop()
                        await t.cleanup()
                    return False

            # Start all triggers (allow partial failures)
            successful_triggers = []
            failed_triggers = []

            for trigger in triggers:
                success = await trigger.start()
                if success:
                    successful_triggers.append(trigger)
                    logger.info(
                        f"✅ Started trigger {trigger.trigger_type} for workflow {workflow_id}"
                    )
                else:
                    failed_triggers.append(trigger)
                    logger.warning(
                        f"⚠️ Failed to start trigger {trigger.trigger_type} for workflow {workflow_id}, continuing with other triggers"
                    )
                    # Clean up the failed trigger
                    await trigger.stop()
                    await trigger.cleanup()

            # If no triggers started successfully, consider it a failure
            if not successful_triggers:
                logger.error(f"❌ No triggers started successfully for workflow {workflow_id}")
                return False

            # Log summary of results
            if failed_triggers:
                logger.warning(
                    f"⚠️ Partial deployment success for workflow {workflow_id}: "
                    f"{len(successful_triggers)} triggers started, {len(failed_triggers)} failed"
                )

            # Store only successful triggers
            self._triggers[workflow_id] = successful_triggers

            logger.info(
                f"Successfully registered {len(successful_triggers)} triggers for workflow {workflow_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Failed to register triggers for workflow {workflow_id}: {e}",
                exc_info=True,
            )
            return False

    async def unregister_triggers(self, workflow_id: str) -> bool:
        """
        Unregister and stop all triggers for a workflow

        Args:
            workflow_id: Workflow identifier

        Returns:
            bool: True if all triggers unregistered successfully
        """
        try:
            triggers = self._triggers.get(workflow_id, [])

            if not triggers:
                logger.debug(f"No triggers to unregister for workflow {workflow_id}")
                return True

            logger.info(f"Unregistering {len(triggers)} triggers for workflow {workflow_id}")

            # Stop and cleanup all triggers
            for trigger in triggers:
                try:
                    await trigger.stop()
                    await trigger.cleanup()
                except Exception as e:
                    logger.warning(f"Error stopping trigger {trigger.trigger_type}: {e}")

            # Remove from registry
            del self._triggers[workflow_id]

            logger.info(f"Successfully unregistered triggers for workflow {workflow_id}")
            return True

        except Exception as e:
            logger.error(
                f"Failed to unregister triggers for workflow {workflow_id}: {e}",
                exc_info=True,
            )
            return False

    async def get_trigger_status(self, workflow_id: str) -> Dict[str, TriggerStatus]:
        """
        Get status of all triggers for a workflow

        Args:
            workflow_id: Workflow identifier

        Returns:
            Dict mapping trigger types to their status
        """
        triggers = self._triggers.get(workflow_id, [])
        status = {}

        for trigger in triggers:
            status[trigger.trigger_type] = trigger.status

        return status

    async def trigger_manual(
        self, workflow_id: str, user_id: str, access_token: Optional[str] = None
    ) -> WorkflowExecutionResponse:
        """
        Manually trigger a workflow execution

        Args:
            workflow_id: Workflow to trigger
            user_id: User requesting the trigger

        Returns:
            ExecutionResult with execution details
        """
        try:
            triggers = self._triggers.get(workflow_id, [])
            manual_triggers = [
                t for t in triggers if t.trigger_type == TriggerSubtype.MANUAL.value and t.enabled
            ]

            if not manual_triggers:
                return WorkflowExecutionResponse(
                    execution_id=f"exec_{workflow_id}",
                    workflow_id=workflow_id,
                    status="failed",
                    message="No active manual trigger found for workflow",
                )

            # Use the first manual trigger
            manual_trigger = manual_triggers[0]

            # Call the manual trigger's specific method
            if hasattr(manual_trigger, "trigger_manual"):
                return await manual_trigger.trigger_manual(user_id, access_token)
            else:
                # Fallback to base trigger method
                return await manual_trigger._trigger_workflow(
                    {"trigger_type": TriggerSubtype.MANUAL.value, "user_id": user_id},
                    access_token=access_token,
                )

        except Exception as e:
            logger.error(f"Manual trigger failed for workflow {workflow_id}: {e}", exc_info=True)
            return WorkflowExecutionResponse(
                execution_id=f"exec_{workflow_id}",
                workflow_id=workflow_id,
                status=ExecutionStatus.ERROR,
                message=f"Manual trigger error: {str(e)}",
            )

    async def process_webhook(
        self, workflow_id: str, request_data: Dict[str, Any]
    ) -> WorkflowExecutionResponse:
        """
        Process webhook trigger for a workflow

        Args:
            workflow_id: Workflow to trigger
            request_data: HTTP request data

        Returns:
            ExecutionResult with execution details
        """
        try:
            triggers = self._triggers.get(workflow_id, [])
            webhook_triggers = [
                t for t in triggers if t.trigger_type == TriggerSubtype.WEBHOOK.value and t.enabled
            ]

            if not webhook_triggers:
                return WorkflowExecutionResponse(
                    execution_id=f"exec_{workflow_id}",
                    workflow_id=workflow_id,
                    status="failed",
                    message="No active webhook trigger found for workflow",
                )

            # Use the first webhook trigger
            webhook_trigger = webhook_triggers[0]

            # Call the webhook trigger's specific method
            if hasattr(webhook_trigger, "process_webhook"):
                return await webhook_trigger.process_webhook(request_data)
            else:
                # Fallback to base trigger method
                return await webhook_trigger._trigger_workflow(request_data)

        except Exception as e:
            logger.error(f"Webhook trigger failed for workflow {workflow_id}: {e}", exc_info=True)
            return WorkflowExecutionResponse(
                execution_id=f"exec_{workflow_id}",
                workflow_id=workflow_id,
                status=ExecutionStatus.ERROR,
                message=f"Webhook trigger error: {str(e)}",
            )

    async def health_check(self) -> Dict[str, Any]:
        """Get health status of all managed triggers"""
        health_status = {
            "total_workflows": len(self._triggers),
            "total_triggers": sum(len(triggers) for triggers in self._triggers.values()),
            "workflows": {},
        }

        for workflow_id, triggers in self._triggers.items():
            workflow_health = {"trigger_count": len(triggers), "triggers": {}}

            for trigger in triggers:
                trigger_health = await trigger.health_check()
                workflow_health["triggers"][trigger.trigger_type] = trigger_health

            health_status["workflows"][workflow_id] = workflow_health

        return health_status

    async def cleanup(self) -> None:
        """Cleanup all triggers and resources"""
        logger.info("Cleaning up TriggerManager")

        for workflow_id in list(self._triggers.keys()):
            await self.unregister_triggers(workflow_id)

        logger.info("TriggerManager cleanup complete")

    async def process_github_webhook(
        self,
        event_type: str,
        delivery_id: str,
        payload: dict,
        signature: Optional[str] = None,
    ) -> dict:
        """
        Process GitHub webhook events across all workflows

        Args:
            event_type: GitHub event type (push, pull_request, etc.)
            delivery_id: GitHub delivery ID
            payload: GitHub webhook payload
            signature: GitHub webhook signature for verification

        Returns:
            Dictionary with processing results
        """
        try:
            logger.info(f"Processing GitHub webhook: {event_type} (delivery: {delivery_id})")

            results = []
            processed_workflows = 0

            # Process all workflows that have GitHub triggers
            for workflow_id, triggers in self._triggers.items():
                github_triggers = [
                    t
                    for t in triggers
                    if t.trigger_type == TriggerSubtype.GITHUB.value and t.enabled
                ]

                for trigger in github_triggers:
                    try:
                        # Check if this trigger should handle this event type
                        if hasattr(trigger, "should_trigger_for_event"):
                            if not trigger.should_trigger_for_event(event_type, payload):
                                continue

                        # Trigger the workflow
                        trigger_data = {
                            "event_type": event_type,
                            "delivery_id": delivery_id,
                            "payload": payload,
                            "signature": signature,
                        }

                        result = await trigger._trigger_workflow(trigger_data)
                        results.append(
                            {
                                "workflow_id": workflow_id,
                                "execution_id": result.execution_id,
                                "status": result.status,
                                "message": result.message,
                            }
                        )
                        processed_workflows += 1

                        logger.info(
                            f"GitHub webhook triggered workflow {workflow_id}: {result.execution_id}"
                        )

                    except Exception as e:
                        logger.error(
                            f"Error processing GitHub webhook for workflow {workflow_id}: {e}",
                            exc_info=True,
                        )
                        results.append(
                            {
                                "workflow_id": workflow_id,
                                "execution_id": None,
                                "status": "failed",
                                "message": f"GitHub webhook processing failed: {str(e)}",
                            }
                        )

            return {
                "processed_workflows": processed_workflows,
                "results": results,
                "event_type": event_type,
                "delivery_id": delivery_id,
            }

        except Exception as e:
            logger.error(f"Error processing GitHub webhook {event_type}: {e}", exc_info=True)
            raise

    async def route_and_trigger_cron_event(
        self, cron_expression: str, timezone: str = "UTC"
    ) -> Dict[str, Any]:
        """
        Use EventRouter to find and trigger workflows matching a cron expression

        Args:
            cron_expression: Cron expression that triggered
            timezone: Timezone for the cron execution

        Returns:
            Dictionary with trigger results
        """
        try:
            logger.info(f"Processing cron event via EventRouter: {cron_expression}")

            # Use EventRouter for fast trigger matching
            matching_workflows = await self.event_router.route_cron_event(cron_expression, timezone)

            results = []
            for workflow_match in matching_workflows:
                workflow_id = workflow_match["workflow_id"]
                trigger_data = workflow_match["trigger_data"]

                # In testing mode, send notification instead of executing
                result = await self.notification_service.send_trigger_notification(
                    workflow_id=workflow_id,
                    trigger_type="CRON_TRIGGER",
                    trigger_data=trigger_data,
                )

                results.append(
                    {
                        "workflow_id": workflow_id,
                        "status": result.status,
                        "message": result.message,
                        "trigger_data": trigger_data,
                    }
                )

                logger.info(f"Cron trigger processed for workflow {workflow_id}: {result.status}")

            return {
                "processed_workflows": len(results),
                "results": results,
                "cron_expression": cron_expression,
                "timezone": timezone,
            }

        except Exception as e:
            logger.error(f"Error processing cron event {cron_expression}: {e}", exc_info=True)
            raise

    async def route_and_trigger_webhook_event(
        self,
        path: str,
        method: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        remote_addr: str,
    ) -> Dict[str, Any]:
        """
        Use EventRouter to find and trigger workflows matching a webhook request

        Args:
            path: Webhook URL path
            method: HTTP method
            headers: Request headers
            payload: Request payload
            remote_addr: Remote IP address

        Returns:
            Dictionary with trigger results
        """
        try:
            logger.info(f"Processing webhook event via EventRouter: {method} {path}")

            # Use EventRouter for fast trigger matching
            matching_workflows = await self.event_router.route_webhook_event(
                path, method, headers, payload, remote_addr
            )

            results = []
            for workflow_match in matching_workflows:
                workflow_id = workflow_match["workflow_id"]
                trigger_data = workflow_match["trigger_data"]

                # In testing mode, send notification instead of executing
                result = await self.notification_service.send_trigger_notification(
                    workflow_id=workflow_id,
                    trigger_type="WEBHOOK_TRIGGER",
                    trigger_data=trigger_data,
                )

                results.append(
                    {
                        "workflow_id": workflow_id,
                        "status": result.status,
                        "message": result.message,
                        "trigger_data": trigger_data,
                    }
                )

                logger.info(
                    f"Webhook trigger processed for workflow {workflow_id}: {result.status}"
                )

            return {
                "processed_workflows": len(results),
                "results": results,
                "path": path,
                "method": method,
            }

        except Exception as e:
            logger.error(f"Error processing webhook event {path}: {e}", exc_info=True)
            raise

    async def route_and_trigger_github_event(
        self,
        event_type: str,
        delivery_id: str,
        payload: Dict[str, Any],
        signature: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Use EventRouter to find and trigger workflows matching a GitHub webhook

        Args:
            event_type: GitHub event type (push, pull_request, etc.)
            delivery_id: GitHub delivery ID
            payload: GitHub webhook payload
            signature: GitHub webhook signature

        Returns:
            Dictionary with trigger results
        """
        try:
            logger.info(
                f"Processing GitHub event via EventRouter: {event_type} (delivery: {delivery_id})"
            )

            # Use EventRouter for fast trigger matching
            matching_workflows = await self.event_router.route_github_event(
                event_type, delivery_id, payload, signature
            )

            results = []
            for workflow_match in matching_workflows:
                workflow_id = workflow_match["workflow_id"]
                trigger_data = workflow_match["trigger_data"]

                # In testing mode, send notification instead of executing
                result = await self.notification_service.send_trigger_notification(
                    workflow_id=workflow_id,
                    trigger_type="GITHUB_TRIGGER",
                    trigger_data=trigger_data,
                )

                results.append(
                    {
                        "workflow_id": workflow_id,
                        "status": result.status,
                        "message": result.message,
                        "trigger_data": trigger_data,
                    }
                )

                logger.info(f"GitHub trigger processed for workflow {workflow_id}: {result.status}")

            return {
                "processed_workflows": len(results),
                "results": results,
                "event_type": event_type,
                "delivery_id": delivery_id,
            }

        except Exception as e:
            logger.error(f"Error processing GitHub event {event_type}: {e}", exc_info=True)
            raise

    async def route_and_trigger_email_event(
        self,
        sender: str,
        subject: str,
        body: str,
        recipients: List[str],
        headers: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Use EventRouter to find and trigger workflows matching an email

        Args:
            sender: Email sender address
            subject: Email subject line
            body: Email body content
            recipients: List of recipient addresses
            headers: Email headers

        Returns:
            Dictionary with trigger results
        """
        try:
            logger.info(f"Processing email event via EventRouter from: {sender}")

            # Use EventRouter for fast trigger matching
            matching_workflows = await self.event_router.route_email_event(
                sender, subject, body, recipients, headers
            )

            results = []
            for workflow_match in matching_workflows:
                workflow_id = workflow_match["workflow_id"]
                trigger_data = workflow_match["trigger_data"]

                # In testing mode, send notification instead of executing
                result = await self.notification_service.send_trigger_notification(
                    workflow_id=workflow_id,
                    trigger_type="EMAIL_TRIGGER",
                    trigger_data=trigger_data,
                )

                results.append(
                    {
                        "workflow_id": workflow_id,
                        "status": result.status,
                        "message": result.message,
                        "trigger_data": trigger_data,
                    }
                )

                logger.info(f"Email trigger processed for workflow {workflow_id}: {result.status}")

            return {
                "processed_workflows": len(results),
                "results": results,
                "sender": sender,
                "subject": subject,
            }

        except Exception as e:
            logger.error(f"Error processing email event from {sender}: {e}", exc_info=True)
            raise

    async def _create_trigger(self, workflow_id: str, spec: TriggerSpec) -> Optional[BaseTrigger]:
        """
        Create a trigger instance from specification

        Args:
            workflow_id: Workflow identifier
            spec: Trigger specification

        Returns:
            BaseTrigger instance or None if creation failed
        """
        try:
            trigger_class = self._trigger_registry.get(spec.subtype)
            if not trigger_class:
                logger.error(f"No trigger class registered for type: {spec.subtype}")
                return None

            # Create trigger config
            trigger_config = {"enabled": spec.enabled, **spec.parameters}

            # Add lock manager to config
            trigger_config["lock_manager"] = self.lock_manager

            # Create trigger instance
            trigger = trigger_class(workflow_id, trigger_config)

            logger.debug(f"Created trigger {spec.subtype.value} for workflow {workflow_id}")
            return trigger

        except Exception as e:
            logger.error(f"Failed to create trigger {spec.subtype.value}: {e}", exc_info=True)
            return None
