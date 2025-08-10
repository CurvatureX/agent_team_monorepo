# OAuth2 Configuration Guide

## Required Environment Variables

To use the External Action Node OAuth2 integration, you need to configure the following environment variables:

### Google Calendar Integration
```bash
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
```

### GitHub Integration  
```bash
GITHUB_CLIENT_ID="your-github-client-id"
GITHUB_CLIENT_SECRET="your-github-client-secret"
```

### Slack Integration
```bash
SLACK_CLIENT_ID="your-slack-client-id"  
SLACK_CLIENT_SECRET="your-slack-client-secret"
```

### Credential Encryption
```bash
CREDENTIAL_ENCRYPTION_KEY="your-32-byte-base64-key"
```

## Frontend Configuration

For the frontend to work properly, set these environment variables in your `.env.local`:

```bash
NEXT_PUBLIC_GOOGLE_CLIENT_ID="your-google-client-id"
```

## Obtaining OAuth2 Credentials

### Google Calendar
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Calendar API
4. Create OAuth2 credentials
5. Add authorized redirect URIs:
   - `http://localhost:3003/oauth-callback` (development)
   - Your production callback URL

### GitHub
1. Go to [GitHub Settings > Developer settings](https://github.com/settings/developers)
2. Create a new OAuth App
3. Set callback URL to your redirect URI

### Slack
1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app
3. Configure OAuth & Permissions
4. Add required scopes: `chat:write`, `channels:read`

## Security Notes

- Never commit OAuth client secrets to version control
- Use environment variables for all sensitive configuration
- Rotate credentials regularly
- Use different credentials for development and production