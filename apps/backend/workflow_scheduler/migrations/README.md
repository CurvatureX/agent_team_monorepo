# Slack Channel Name Migration

This migration updates existing Slack triggers to convert channel names (like "hil", "general") to channel IDs (like "C09D2JW6814") for improved performance and reliability.

## Why This Migration Is Needed

- **Performance**: Converting channel names to IDs at deployment time eliminates runtime API calls
- **Reliability**: Reduces dependency on Slack API availability and OAuth scopes during trigger processing
- **Consistency**: Aligns with the new deployment-time channel resolution system

## Running the Migration

### 1. Dry Run (Recommended First)

```bash
# Run from the workflow_scheduler directory
cd apps/backend/workflow_scheduler

# See what would be changed without making actual updates
python migrations/migrate_slack_channel_names.py --dry-run
```

### 2. Full Migration

```bash
# Run the actual migration
python migrations/migrate_slack_channel_names.py
```

### 3. Migrate Specific Workflow

```bash
# Only migrate a specific workflow ID
python migrations/migrate_slack_channel_names.py --workflow-id 5cfba322-0888-41b7-97c3-53620a14d46c
```

### 4. Docker Environment

```bash
# If running in Docker, exec into the container first
docker exec -it workflow-scheduler bash
cd /app/workflow_scheduler
python migrations/migrate_slack_channel_names.py --dry-run
```

## What the Migration Does

### Before Migration:
```json
{
  "channel_filter": "hil"
}
```

### After Migration:
```json
{
  "channel_filter": "C09D2JW6814"
}
```

## Migration Process

1. **Query**: Finds all active Slack triggers in `trigger_index` table
2. **Group**: Groups triggers by workflow owner (user_id)
3. **Resolve**: Uses each user's Slack OAuth token to resolve channel names to IDs
4. **Update**: Updates the `trigger_config` in the database with resolved channel IDs
5. **Report**: Provides detailed statistics on migration results

## Safety Features

- **Dry Run Mode**: Test the migration without making changes
- **Smart Detection**: Skips triggers that already have channel IDs
- **Fallback**: Keeps original names if resolution fails
- **Comprehensive Logging**: Detailed logs for debugging
- **Statistics**: Clear summary of migration results

## Expected Output

```
🚀 Starting Slack channel name migration
📊 Found 4 Slack triggers to examine
👥 Processing triggers for 2 users
👤 Processing 3 triggers for user 7ba36345-a2bb-4ec9-a001-bb46d79d629d
🔄 Migrating trigger eee23087-7853-429f-a443-450b42b39d20: 'hil' → channel IDs
✅ Successfully migrated eee23087-7853-429f-a443-450b42b39d20: 'hil' → 'C09D2JW6814'
🏁 Migration completed!
📊 Migration Summary:
   📋 Total triggers examined: 4
   🔄 Triggers needing migration: 2
   ✅ Successful migrations: 2
   ❌ Failed migrations: 0
   ⏭️ Skipped triggers: 2
```

## Troubleshooting

### No Slack OAuth Token Found
- User needs to re-authorize Slack integration
- Check `oauth_tokens` table for active Slack integrations

### Channel Not Found
- Channel may have been deleted or renamed
- User may not have access to private channels
- Check Slack workspace for channel existence

### API Rate Limits
- Migration includes reasonable delays between API calls
- Slack API has generous rate limits for conversations.list

## Rollback

If needed, you can manually revert changes by updating the `trigger_config` back to channel names:

```sql
UPDATE trigger_index
SET trigger_config = jsonb_set(trigger_config, '{channel_filter}', '"hil"')
WHERE workflow_id = 'your-workflow-id' AND trigger_type = 'SLACK';
```

## Post-Migration

After successful migration:
1. New Slack triggers will automatically get channel IDs during deployment
2. Existing triggers will use fast channel ID comparison
3. Runtime Slack event processing will be significantly faster
4. No more OAuth scope dependencies during trigger processing
