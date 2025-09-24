# Manual Trigger Invocation Integration

This document describes the integration of the manual trigger invocation system into the Workflow Execution Monitor demo app.

## 🎯 Overview

The integration enables users to manually invoke any trigger node in a workflow directly from the React Flow visualization. When clicking on a trigger node, users can access a dynamic form that allows them to set custom parameters and execute the workflow.

## ✨ Features

### 1. Enhanced Node Detail Modal
- **Trigger Detection**: Automatically detects when a TRIGGER node is clicked
- **Tabbed Interface**: Shows "Node Details" and "Manual Trigger" tabs for trigger nodes
- **Visual Indicator**: Displays a "Trigger Node" badge for easy identification

### 2. Dynamic Parameter Form
- **Schema Discovery**: Automatically loads parameter schema from the backend
- **Form Generation**: Creates dynamic forms based on JSON Schema
- **Parameter Types**: Supports strings, numbers, objects, enums, and more
- **Examples**: Quick-load buttons for common parameter configurations
- **Validation**: Client-side parameter validation using JSON Schema

### 3. Real-time Execution
- **One-Click Invocation**: Execute workflows with custom parameters
- **Execution Tracking**: Returns execution ID for monitoring
- **Success Feedback**: Shows execution results and provides links
- **Error Handling**: Displays clear error messages for failed invocations

## 🔧 Technical Implementation

### API Client Extensions (`src/services/api.ts`)
```typescript
// Get manual invocation schema for a trigger node
async getManualInvocationSchema(workflowId: string, triggerNodeId: string)

// Manually invoke a trigger with parameters
async manualInvokeTrigger(workflowId: string, triggerNodeId: string, data: {...})
```

### New Components

#### TriggerInvocationForm (`src/components/ui/TriggerInvocationForm.tsx`)
- **Dynamic Form Rendering**: Creates forms based on JSON Schema
- **Parameter Management**: Handles different parameter types (string, number, object, enum)
- **Example Loading**: Allows users to quickly load example configurations
- **Real-time Validation**: Validates parameters against schema before submission
- **Execution Results**: Shows success/error states with execution details

#### Enhanced NodeDetailModal (`src/components/workflow/WorkflowVisualization.tsx`)
- **Tab Navigation**: Switches between node details and trigger form
- **Conditional Rendering**: Only shows trigger tab for TRIGGER nodes
- **Workflow Context**: Passes workflow ID to enable trigger invocation

## 🚀 Usage Flow

### For End Users:
1. **Open Workflow**: Navigate to any workflow in the execution monitor
2. **Click Trigger Node**: Click on any trigger node in the React Flow visualization
3. **Switch to Manual Trigger Tab**: Click the "Manual Trigger" tab in the modal
4. **Configure Parameters**:
   - Use quick examples or manually set parameters
   - Add a description for the execution
   - Fill in required fields based on the trigger type
5. **Invoke Trigger**: Click "Invoke Trigger" to start execution
6. **Monitor Execution**: Use the returned execution ID to track progress

### Supported Trigger Types:
- **WEBHOOK**: HTTP method, headers, body, query parameters
- **SLACK**: Event type, message, user, channel, thread
- **EMAIL**: From, subject, body, attachments
- **GITHUB**: Event type, repository, ref, payload
- **CRON**: Scheduled time, context data
- **MANUAL**: Trigger context, description

## 🔗 Backend Integration

The frontend integrates with the manual trigger invocation system implemented in the backend:

### API Endpoints Used:
- `GET /api/v1/app/workflows/{workflowId}/triggers/{triggerNodeId}/manual-invocation-schema`
- `POST /api/v1/app/workflows/{workflowId}/triggers/{triggerNodeId}/manual-invoke`

### Authentication:
- Uses existing Supabase JWT token authentication
- Automatically handles token refresh through the API client

## 📋 Example Usage

### Webhook Trigger Example:
```json
{
  "method": "POST",
  "headers": {
    "Content-Type": "application/json",
    "Authorization": "Bearer token123"
  },
  "body": {
    "user_id": "12345",
    "action": "user_signup",
    "timestamp": "2025-01-13T10:30:00Z"
  },
  "query_params": {}
}
```

### Slack Trigger Example:
```json
{
  "event_type": "message",
  "message": "Hello from manual trigger!",
  "user_id": "U1234567890",
  "channel_id": "C1234567890"
}
```

### Email Trigger Example:
```json
{
  "from": "customer@example.com",
  "subject": "Support Request - Manual Test",
  "body": "This is a test support request from the manual trigger",
  "to": "support@company.com"
}
```

## 🎨 UI/UX Features

### Visual Design:
- **Consistent Styling**: Uses existing design system and color schemes
- **Loading States**: Shows spinners during schema loading and execution
- **Success States**: Clear success feedback with execution details
- **Error States**: User-friendly error messages with retry options

### Animations:
- **Smooth Transitions**: Framer Motion animations for modal interactions
- **Loading Indicators**: Animated loading states during API calls
- **Success Animations**: Celebration animations for successful executions

## 🧪 Testing

### Manual Testing Steps:
1. **Authentication**: Ensure user is properly authenticated
2. **Workflow Loading**: Verify workflows load with trigger nodes
3. **Schema Loading**: Click trigger nodes and verify schema loads
4. **Form Interaction**: Test parameter input with different types
5. **Example Loading**: Test quick example loading functionality
6. **Execution**: Test actual trigger invocation with valid parameters
7. **Error Handling**: Test with invalid parameters to verify error handling

### Supported Browsers:
- Chrome 90+
- Firefox 90+
- Safari 14+
- Edge 90+

## 🔧 Configuration

### Environment Variables:
The integration uses existing environment variables for API communication:
- `NEXT_PUBLIC_API_URL`: Backend API URL (via proxy)
- Supabase configuration for authentication

### No Additional Setup Required:
The integration automatically uses the existing authentication and API infrastructure.

## 🎉 Benefits

### For Users:
- **Easy Testing**: Test workflows without external triggers
- **Debugging**: Simulate different trigger scenarios
- **Development**: Rapid workflow iteration and testing
- **Training**: Learn workflow behavior with safe manual execution

### For Developers:
- **Integration Ready**: Works with existing authentication and API
- **Type Safe**: Full TypeScript support with proper types
- **Extensible**: Easy to add new trigger types or parameters
- **Maintainable**: Clean separation of concerns and reusable components

## 🔮 Future Enhancements

Potential improvements for the manual trigger system:

1. **Parameter History**: Save and reuse previous parameter sets
2. **Bulk Execution**: Trigger multiple workflows simultaneously
3. **Scheduled Triggers**: Schedule manual triggers for future execution
4. **Parameter Validation**: Enhanced validation with custom rules
5. **Template Management**: Create and save parameter templates
6. **Execution Analytics**: Track manual trigger usage and success rates

---

The manual trigger invocation system provides a powerful and user-friendly way to interact with workflows, enabling better testing, debugging, and operational control over workflow executions.
