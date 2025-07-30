#!/usr/bin/env python3
"""
Data Mapping System Demo

This demo showcases the complete data mapping system functionality
with realistic workflow scenarios.
"""

import json
import os
import sys
from datetime import datetime

# Add workflow_engine to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from workflow_engine.data_mapping import (
    ConnectionExecutor,
    DataMapping,
    DataMappingProcessor,
    ExecutionContext,
    FieldMapping,
    FieldTransform,
    MappingType,
    NodeExecutionResult,
    TransformType,
)


def demo_customer_service_workflow():
    """Demo a complete customer service workflow with data transformations."""
    print("🎯 Customer Service Workflow Demo")
    print("-" * 50)

    # Initialize the data mapping processor
    processor = DataMappingProcessor()
    context = ExecutionContext(
        workflow_id="customer_service_wf_001",
        execution_id="exec_20250129_001",
        node_id="ai_router",
        current_time=datetime.now().isoformat(),
        user_id="customer_123",
        session_id="session_456",
    )

    print("📋 Scenario: Customer submits a technical support request")

    # Step 1: Router Agent Output
    router_output = {
        "route": "technical_support",
        "confidence": 0.94,
        "reasoning": "Customer reported API integration issues and provided error logs",
        "metadata": {
            "customer_id": "cust_enterprise_789",
            "customer_tier": "enterprise",
            "support_history": {
                "previous_tickets": 3,
                "satisfaction_score": 4.2,
                "last_contact": "2025-01-25T14:30:00Z",
            },
            "request_details": {
                "urgency": "high",
                "category": "api_integration",
                "affected_systems": ["payment_api", "webhook_handler"],
            },
        },
    }

    print("🤖 Router Agent Output:")
    print(json.dumps(router_output, indent=2))

    # Step 2: Transform for Task Analyzer
    print("\n🔄 Transforming for Task Analyzer...")

    task_analyzer_mapping = DataMapping(
        type=MappingType.FIELD_MAPPING,
        description="Transform router output to task analyzer input",
        field_mappings=[
            # Basic routing information
            FieldMapping(source_field="route", target_field="task_category", required=True),
            FieldMapping(source_field="reasoning", target_field="task_description"),
            # Priority calculation based on confidence and customer tier
            FieldMapping(
                source_field="confidence",
                target_field="priority_score",
                transform=FieldTransform(
                    type=TransformType.CONDITION,
                    transform_value="{{value}} > 0.9 ? 'critical' : ({{value}} > 0.7 ? 'high' : 'medium')",
                ),
            ),
            # Customer information extraction
            FieldMapping(source_field="metadata.customer_id", target_field="customer.id"),
            FieldMapping(source_field="metadata.customer_tier", target_field="customer.tier"),
            FieldMapping(
                source_field="metadata.support_history.previous_tickets",
                target_field="customer.history.ticket_count",
            ),
            FieldMapping(
                source_field="metadata.support_history.satisfaction_score",
                target_field="customer.history.satisfaction",
                transform=FieldTransform(
                    type=TransformType.FUNCTION,
                    transform_value="math_round",
                    options={"digits": "1"},
                ),
            ),
            # Request analysis
            FieldMapping(
                source_field="metadata.request_details.urgency",
                target_field="analysis.urgency_stated",
            ),
            FieldMapping(
                source_field="metadata.request_details.category", target_field="analysis.category"
            ),
            FieldMapping(
                source_field="metadata.request_details.affected_systems",
                target_field="analysis.affected_systems",
            ),
        ],
        static_values={
            "analysis.processed_at": "{{current_time}}",
            "analysis.workflow_id": "{{workflow_id}}",
            "analysis.source_node": "ai_router",
            "analysis.session_id": "{{session_id}}",
            "analysis.auto_escalate": "false",
        },
    )

    task_analyzer_input = processor.transform_data(router_output, task_analyzer_mapping, context)

    print("📊 Task Analyzer Input:")
    print(json.dumps(task_analyzer_input, indent=2))

    # Step 3: Task Analyzer Processing (simulated output)
    print("\n🧠 Task Analyzer Processing...")

    task_analyzer_output = {
        "task_type": "technical_integration_issue",
        "complexity_score": 8.5,
        "estimated_resolution_time": 240,  # minutes
        "required_expertise": ["api_integration", "payment_systems", "webhook_debugging"],
        "suggested_actions": [
            "Review API integration logs",
            "Check webhook endpoint configuration",
            "Validate payment system connectivity",
            "Escalate to senior developer if needed",
        ],
        "risk_assessment": {
            "business_impact": "high",
            "technical_risk": "medium",
            "customer_satisfaction_risk": "high",
        },
        "resource_requirements": {
            "engineer_level": "senior",
            "estimated_hours": 4,
            "tools_needed": ["log_analyzer", "api_testing_suite"],
        },
    }

    print("🔍 Task Analyzer Output:")
    print(json.dumps(task_analyzer_output, indent=2))

    # Step 4: Transform for Ticket Creation System
    print("\n🎫 Transforming for Ticket Creation...")

    context.node_id = "task_analyzer"  # Update context for next transformation

    ticket_creation_mapping = DataMapping(
        type=MappingType.TEMPLATE,
        description="Generate comprehensive ticket from analysis",
        transform_script="""{
            "ticket": {
                "id": "TICK-{{workflow_id}}-{{current_time | date_format('YYYYMMDDHHMMSS')}}",
                "title": "{{task_category | string_upper}} - {{task_description | truncate(50)}}",
                "description": "{{task_description}}",
                "priority": "{{priority_score}}",
                "category": "{{analysis.category}}",
                "urgency": "{{analysis.urgency_stated}}",
                "created_at": "{{current_time}}",
                "status": "open"
            },
            "customer": {
                "id": "{{customer.id}}",
                "tier": "{{customer.tier}}",
                "satisfaction_history": {{customer.history.satisfaction}},
                "previous_tickets": {{customer.history.ticket_count}}
            },
            "assignment": {
                "queue": "technical_support",
                "required_skills": "{{required_expertise | array_join(', ')}}",
                "estimated_hours": {{resource_requirements.estimated_hours}},
                "engineer_level": "{{resource_requirements.engineer_level}}"
            },
            "metadata": {
                "workflow_id": "{{workflow_id}}",
                "session_id": "{{session_id}}",
                "complexity_score": {{complexity_score}},
                "business_impact": "{{risk_assessment.business_impact}}",
                "affected_systems": "{{analysis.affected_systems | array_join(', ')}}",
                "auto_escalate": false
            }
        }""",
    )

    # Combine previous inputs for template processing
    combined_data = {**task_analyzer_input, **task_analyzer_output}

    ticket_data = processor.transform_data(combined_data, ticket_creation_mapping, context)

    print("🎫 Ticket Creation Data:")
    print(json.dumps(ticket_data, indent=2))

    # Step 5: Connection Executor Demo
    print("\n🔗 Connection Executor Demo...")

    executor = ConnectionExecutor()

    # Simulate source node result
    source_result = NodeExecutionResult(
        node_id="task_analyzer",
        status="SUCCESS",
        output_data=task_analyzer_output,
        execution_time=1.2,
    )

    # Mock target node
    target_node = type("Node", (), {"id": "ticket_system"})()

    # Create connection with complex mapping
    from workflow_engine.data_mapping.executors import Connection

    connection = Connection(
        node="ticket_system",
        source_port="main",
        target_port="main",
        data_mapping=DataMapping(
            type=MappingType.FIELD_MAPPING,
            field_mappings=[
                FieldMapping(source_field="task_type", target_field="ticket.category"),
                FieldMapping(
                    source_field="complexity_score",
                    target_field="ticket.complexity",
                    transform=FieldTransform(
                        type=TransformType.CONDITION,
                        transform_value="{{value}} > 8 ? 'high' : ({{value}} > 5 ? 'medium' : 'low')",
                    ),
                ),
                FieldMapping(
                    source_field="estimated_resolution_time",
                    target_field="ticket.sla_hours",
                    transform=FieldTransform(
                        type=TransformType.FUNCTION,
                        transform_value="math_round",
                        options={"digits": "0"},
                    ),
                ),
                FieldMapping(
                    source_field="required_expertise",
                    target_field="ticket.skills_required",
                    transform=FieldTransform(
                        type=TransformType.FUNCTION,
                        transform_value="array_join",
                        options={"separator": " | "},
                    ),
                ),
            ],
            static_values={
                "ticket.created_by": "ai_workflow",
                "ticket.priority": "high",
                "ticket.status": "new",
            },
        ),
    )

    ticket_result = executor.execute_connection(source_result, connection, target_node, context)

    print("🎫 Final Ticket Data:")
    print(json.dumps(ticket_result, indent=2))

    print("\n✅ Customer Service Workflow Demo Complete!")
    return True


def demo_data_transformation_patterns():
    """Demo various data transformation patterns."""
    print("\n🔧 Data Transformation Patterns Demo")
    print("-" * 50)

    processor = DataMappingProcessor()
    context = ExecutionContext.create_default("demo_wf", "demo_exec", "demo_node")

    # Sample e-commerce order data
    order_data = {
        "order_id": "ORD-2025-001234",
        "customer": {
            "id": "cust_789",
            "email": "customer@example.com",
            "tier": "premium",
            "address": {
                "street": "123 Main St",
                "city": "San Francisco",
                "state": "CA",
                "zip": "94105",
            },
        },
        "items": [
            {"sku": "PROD-001", "name": "Laptop Pro", "price": 1299.99, "quantity": 1},
            {"sku": "PROD-002", "name": "Wireless Mouse", "price": 79.99, "quantity": 2},
            {"sku": "PROD-003", "name": "USB-C Hub", "price": 49.99, "quantity": 1},
        ],
        "payment": {"method": "credit_card", "last4": "1234", "amount": 1509.96, "currency": "USD"},
        "shipping": {
            "method": "express",
            "cost": 15.00,
            "estimated_delivery": "2025-01-30T18:00:00Z",
        },
    }

    print("📦 Original Order Data:")
    print(json.dumps(order_data, indent=2))

    # Pattern 1: Field Extraction and Restructuring
    print("\n🔄 Pattern 1: Field Extraction and Restructuring")

    inventory_mapping = DataMapping(
        type=MappingType.FIELD_MAPPING,
        field_mappings=[
            FieldMapping(source_field="order_id", target_field="transaction.reference"),
            FieldMapping(source_field="customer.id", target_field="transaction.customer_id"),
            # Extract first item for priority processing
            FieldMapping(source_field="items[0].sku", target_field="priority_item.sku"),
            FieldMapping(
                source_field="items[0].quantity", target_field="priority_item.requested_qty"
            ),
            # Calculate total items
            FieldMapping(
                source_field="items",
                target_field="summary.total_items",
                transform=FieldTransform(
                    type=TransformType.FUNCTION, transform_value="array_length"
                ),
            ),
            # Format shipping address
            FieldMapping(
                source_field="customer.address.street", target_field="shipping.address_line_1"
            ),
            FieldMapping(source_field="customer.address.city", target_field="shipping.city"),
            FieldMapping(source_field="customer.address.state", target_field="shipping.state"),
        ],
        static_values={
            "transaction.type": "order_fulfillment",
            "transaction.processed_at": "{{current_time}}",
            "shipping.priority": "standard",
        },
    )

    inventory_data = processor.transform_data(order_data, inventory_mapping, context)
    print("📋 Inventory System Data:")
    print(json.dumps(inventory_data, indent=2))

    # Pattern 2: Template-based Transformation
    print("\n🔄 Pattern 2: Template-based Notification")

    notification_mapping = DataMapping(
        type=MappingType.TEMPLATE,
        transform_script="""{
            "notification": {
                "type": "order_confirmation",
                "recipient": "{{customer.email}}",
                "subject": "Order {{order_id}} Confirmed - Thank You!",
                "priority": "{{customer.tier == 'premium' ? 'high' : 'normal'}}",
                "delivery_method": "email"
            },
            "content": {
                "greeting": "Dear Valued Customer,",
                "message": "Your order {{order_id}} has been confirmed and is being processed.",
                "order_summary": {
                    "total_amount": "${{payment.amount}}",
                    "item_count": {{items | array_length}},
                    "shipping_method": "{{shipping.method | string_upper}}",
                    "estimated_delivery": "{{shipping.estimated_delivery | date_format('MMM DD, YYYY')}}"
                },
                "tracking_info": "You will receive tracking information once your order ships.",
                "footer": "Thank you for your business!"
            },
            "metadata": {
                "customer_tier": "{{customer.tier}}",
                "order_value": {{payment.amount}},
                "sent_at": "{{current_time}}"
            }
        }""",
    )

    notification_data = processor.transform_data(order_data, notification_mapping, context)
    print("📧 Notification Data:")
    print(json.dumps(notification_data, indent=2))

    # Pattern 3: Complex Business Logic
    print("\n🔄 Pattern 3: Complex Business Logic Transformation")

    billing_mapping = DataMapping(
        type=MappingType.FIELD_MAPPING,
        field_mappings=[
            # Customer information
            FieldMapping(source_field="customer.id", target_field="billing.customer_id"),
            FieldMapping(source_field="customer.tier", target_field="billing.customer_tier"),
            # Payment processing
            FieldMapping(source_field="payment.amount", target_field="billing.subtotal"),
            FieldMapping(source_field="shipping.cost", target_field="billing.shipping_fee"),
            # Calculate tax (simplified - 8.5% for CA)
            FieldMapping(
                source_field="payment.amount",
                target_field="billing.tax_amount",
                transform=FieldTransform(
                    type=TransformType.CONDITION,
                    transform_value="{{value}} * 0.085",  # Simplified tax calculation
                ),
            ),
            # Determine discount based on customer tier
            FieldMapping(
                source_field="customer.tier",
                target_field="billing.discount_percent",
                transform=FieldTransform(
                    type=TransformType.CONDITION,
                    transform_value="{{value}} == 'premium' ? '10' : ({{value}} == 'gold' ? '5' : '0')",
                ),
            ),
            # Payment method processing
            FieldMapping(
                source_field="payment.method",
                target_field="billing.payment_type",
                transform=FieldTransform(
                    type=TransformType.FUNCTION, transform_value="string_upper"
                ),
            ),
        ],
        static_values={
            "billing.currency": "USD",
            "billing.processed_at": "{{current_time}}",
            "billing.status": "pending",
            "billing.reference": "{{workflow_id}}-{{execution_id}}",
        },
    )

    billing_data = processor.transform_data(order_data, billing_mapping, context)
    print("💳 Billing System Data:")
    print(json.dumps(billing_data, indent=2))

    print("\n✅ Data Transformation Patterns Demo Complete!")
    return True


def demo_error_handling():
    """Demo error handling and validation."""
    print("\n⚠️  Error Handling Demo")
    print("-" * 50)

    processor = DataMappingProcessor()
    context = ExecutionContext.create_default("error_demo", "demo_exec", "demo_node")

    # Test data with missing fields
    incomplete_data = {"partial_field": "exists", "nested": {"present": "value"}}

    print("📝 Testing Missing Required Field...")

    try:
        mapping_with_required = DataMapping(
            type=MappingType.FIELD_MAPPING,
            field_mappings=[
                FieldMapping(
                    source_field="missing_field", target_field="output_field", required=True
                )
            ],
        )

        result = processor.transform_data(incomplete_data, mapping_with_required, context)
        print("❌ Should have failed but didn't")
    except Exception as e:
        print(f"✅ Correctly caught error: {str(e)}")

    print("\n📝 Testing Default Values...")

    mapping_with_defaults = DataMapping(
        type=MappingType.FIELD_MAPPING,
        field_mappings=[
            FieldMapping(
                source_field="missing_field",
                target_field="output_field",
                required=True,
                default_value="default_value",
            ),
            FieldMapping(source_field="partial_field", target_field="existing_field"),
        ],
    )

    result = processor.transform_data(incomplete_data, mapping_with_defaults, context)
    print("✅ Default value handling:")
    print(json.dumps(result, indent=2))

    print("\n📝 Testing Optional Fields...")

    mapping_optional = DataMapping(
        type=MappingType.FIELD_MAPPING,
        field_mappings=[
            FieldMapping(
                source_field="missing_field",
                target_field="optional_field",
                required=False,  # This should be skipped
            ),
            FieldMapping(source_field="partial_field", target_field="existing_field"),
            FieldMapping(source_field="nested.present", target_field="nested_field"),
        ],
    )

    result = processor.transform_data(incomplete_data, mapping_optional, context)
    print("✅ Optional field handling:")
    print(json.dumps(result, indent=2))

    print("\n✅ Error Handling Demo Complete!")
    return True


def main():
    """Run all demos."""
    print("🚀 Data Mapping System Comprehensive Demo")
    print("=" * 60)

    try:
        # Run all demos
        demo_customer_service_workflow()
        demo_data_transformation_patterns()
        demo_error_handling()

        print("\n" + "=" * 60)
        print("🎉 All demos completed successfully!")
        print("\n📚 Key Features Demonstrated:")
        print("  ✅ Field-level mapping with transformations")
        print("  ✅ Template-based data transformation")
        print("  ✅ Connection execution with validation")
        print("  ✅ Complex business logic handling")
        print("  ✅ Error handling and default values")
        print("  ✅ Built-in transformation functions")
        print("  ✅ JSONPath field extraction")
        print("  ✅ Static value injection")
        print("  ✅ Context variable resolution")

        return True

    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
