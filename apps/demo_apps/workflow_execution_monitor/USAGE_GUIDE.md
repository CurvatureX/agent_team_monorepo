# Manual Trigger Usage Guide

## 🚀 How to Use Manual Trigger Invocation

### Step 1: Open the Workflow Execution Monitor
1. Navigate to the workflow execution monitor demo app
2. Ensure you're authenticated (login with your Supabase credentials)
3. Select a workflow from the list

### Step 2: Access the Workflow Visualization
1. The React Flow diagram will display all workflow nodes
2. Look for **green** nodes with a **calendar icon** - these are trigger nodes
3. Trigger nodes will show different subtypes: MANUAL, WEBHOOK, SLACK, EMAIL, GITHUB, CRON

### Step 3: Open Node Details
1. **Click on any trigger node** in the visualization
2. A modal will pop up showing node details
3. You'll see a **"Trigger Node"** badge indicating this is a trigger
4. Notice there are two tabs: **"Node Details"** and **"Manual Trigger"**

### Step 4: Switch to Manual Trigger Tab
1. Click the **"Manual Trigger"** tab
2. The system will automatically load the parameter schema for this trigger type
3. You'll see:
   - Trigger description explaining what manual invocation does
   - Quick example buttons for common configurations
   - Dynamic form fields based on the trigger type

### Step 5: Configure Parameters

#### Option A: Use Quick Examples
1. Click any **example button** to auto-fill parameters
2. Examples include:
   - **Webhook**: "Simple API Webhook", "GitHub Push Webhook"
   - **Slack**: "Simple Message", "Bot Mention"
   - **Email**: "Customer Support Email", "Newsletter Email"
   - **GitHub**: "Push to Main", "Pull Request Opened"

#### Option B: Manual Configuration
1. Fill in the **description** field (optional)
2. Configure parameters based on trigger type:

**Webhook Trigger:**
```
Method: POST
Headers: {"Content-Type": "application/json"}
Body: {"user_id": "123", "action": "signup"}
Query Params: {}
```

**Slack Trigger:**
```
Event Type: message
Message: Hello from manual trigger!
User ID: U1234567890
Channel ID: C1234567890
```

**Email Trigger:**
```
From: customer@example.com
Subject: Support Request
Body: This is a test email
To: support@company.com
```

### Step 6: Invoke the Trigger
1. Click the **"Invoke Trigger"** button
2. The system will:
   - Validate your parameters against the schema
   - Send the trigger request to the backend
   - Show a loading state while processing

### Step 7: View Results

#### Success:
- ✅ **Green checkmark** with "Execution Started!" message
- **Execution ID** displayed with copy button
- **"Invoke Again"** button to run another execution

#### Error:
- ❌ **Red error message** explaining what went wrong
- Common issues:
  - Missing required parameters
  - Invalid parameter format
  - Authentication problems
  - Backend service unavailable

## 🎯 Use Cases

### 1. Testing Workflows
- Test how your workflow responds to different input data
- Validate workflow logic before deploying triggers
- Debug issues by simulating specific scenarios

### 2. Emergency Execution
- Manually trigger workflows when automatic triggers fail
- Execute workflows during maintenance windows
- Run workflows with custom parameters for special cases

### 3. Development & Debugging
- Test parameter validation and handling
- Verify workflow node connections and logic
- Simulate edge cases and error conditions

### 4. Training & Demonstration
- Show stakeholders how workflows respond to different inputs
- Train team members on workflow behavior
- Create reproducible demonstrations

## 🔧 Trigger Type Specific Tips

### Webhook Triggers
- **Test different HTTP methods**: GET, POST, PUT, DELETE
- **Include authentication headers** for secure APIs
- **Use realistic JSON payloads** that match your API expectations
- **Test query parameters** for GET requests

### Slack Triggers
- **Use real channel IDs** for testing (format: C1234567890)
- **Include thread_ts** for testing threaded conversations
- **Test different event types**: message, mention, reaction
- **Use proper user IDs** (format: U1234567890)

### Email Triggers
- **Include realistic email addresses** for testing
- **Test with and without attachments**
- **Use proper email formatting** in the body
- **Test different subject line patterns**

### GitHub Triggers
- **Use realistic repository structures** in payload
- **Test different webhook events**: push, pull_request, release
- **Include proper ref formatting**: refs/heads/main
- **Test with realistic commit data**

### CRON Triggers
- **Use ISO timestamp format** for scheduled_time
- **Include timezone information** when relevant
- **Test different schedule contexts**
- **Simulate missed execution scenarios**

### Manual Triggers
- **Provide descriptive context** in trigger_context
- **Include relevant metadata** for execution tracking
- **Test with minimal and maximal parameter sets**

## ⚠️ Important Notes

1. **Authentication Required**: You must be logged in to invoke triggers
2. **Workflow Permissions**: You can only trigger workflows you have access to
3. **Parameter Validation**: Invalid parameters will be rejected with clear error messages
4. **Execution Tracking**: Each invocation creates a new execution with a unique ID
5. **Rate Limiting**: Manual triggers are subject to API rate limits

## 🐛 Troubleshooting

### "Failed to load trigger schema"
- Check your internet connection
- Verify you're authenticated
- Ensure the workflow ID and trigger node ID are valid
- Try refreshing the page

### "Manual invocation not supported"
- Some trigger types may not support manual invocation
- Check the trigger type - all standard types should be supported
- Contact support if a supported type shows as unsupported

### "Parameter validation failed"
- Check that all required fields are filled
- Verify parameter formats match the expected types
- Use the examples as templates for proper formatting
- Check JSON syntax for object parameters

### "Authentication required"
- Refresh the page to renew your authentication token
- Log out and log back in if issues persist
- Check that your account has workflow access permissions

### "Execution failed to start"
- Verify the workflow is properly deployed
- Check that all workflow dependencies are available
- Ensure the backend services are running
- Contact administrator if problems persist

## 📞 Support

If you encounter issues with manual trigger invocation:

1. **Check the browser console** for detailed error messages
2. **Try the examples first** before custom parameters
3. **Verify your authentication status** in the app
4. **Contact the development team** with specific error messages and steps to reproduce

---

Enjoy using the manual trigger invocation system to test, debug, and operate your workflows! 🎉
