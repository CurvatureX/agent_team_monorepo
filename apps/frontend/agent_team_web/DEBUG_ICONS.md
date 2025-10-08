# Icon Display Debugging Guide

## Problem
Icons are not displaying in the frontend even though the API returns `icon_url` correctly.

## Verification Steps

### 1. Verify API is returning icon_url
```bash
curl -s "http://localhost:8000/api/v1/app/workflows/?active_only=true&limit=1" \
  -H "Authorization: Bearer YOUR_TOKEN" | jq '.workflows[0].icon_url'
```

Expected: `"https://dtijyicuvv7hy.cloudfront.net/X.png"` (where X is 1-11)

### 2. Check Browser Console
Open the browser console (F12) and look for:
- `🔍 First workflow icon_url:` log
- Any errors related to Image loading
- Network tab: Check if image requests are failing

### 3. Check SWR Cache
The useWorkflowsApi hook uses SWR which caches responses. The cache might have old data.

## Solutions

### Solution 1: Clear Browser Cache (Quick Fix)
1. Open browser DevTools (F12)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"
4. OR: Press `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows/Linux)

### Solution 2: Clear SWR Cache (Programmatic)
The page has a "Refresh" button that calls `mutate()` which should clear SWR cache.

### Solution 3: Restart Next.js Dev Server
```bash
cd apps/frontend/agent_team_web
# Kill existing process
pkill -f "next dev"
# Restart
npm run dev
```

### Solution 4: Force Cache Bust (Code Change)
If issues persist, you can force a cache bust by adding a timestamp to API requests:

In `src/lib/api/hooks/useWorkflowsApi.ts`:
```typescript
const queryString = params
  ? '?' + new URLSearchParams({
      ...Object.fromEntries(
        Object.entries(params)
          .filter(([_, v]) => v !== undefined)
          .map(([k, v]) => [k, String(v)])
      ),
      _t: Date.now().toString() // Cache buster
    }).toString()
  : `?_t=${Date.now()}`;
```

## Debug Output

The code has been updated to log workflow data in the console. Look for:

```
🔍 First workflow icon_url: https://dtijyicuvv7hy.cloudfront.net/1.png
🔍 Sample workflow data: {
  "id": "...",
  "name": "...",
  "icon_url": "https://dtijyicuvv7hy.cloudfront.net/1.png",
  ...
}
```

## Common Issues

### Issue 1: Image Component Not Showing Remote Images
**Symptom**: Console shows `icon_url` is present but image doesn't render

**Solution**: Check `next.config.ts` has CloudFront domain:
```typescript
images: {
  remotePatterns: [
    {
      protocol: 'https',
      hostname: 'dtijyicuvv7hy.cloudfront.net',
    },
  ],
}
```
✅ This is already configured correctly.

### Issue 2: SWR Stale Data
**Symptom**: Console shows old data without `icon_url`

**Solution**:
1. Click the refresh button in the UI
2. Or clear browser cache
3. Or restart Next.js dev server

### Issue 3: TypeScript Type Mismatch
**Symptom**: TypeScript errors about `icon_url` not existing

**Solution**: Check `src/types/workflow.ts` has:
```typescript
export interface WorkflowSummary {
  // ...
  icon_url?: string | null;
  // ...
}
```
✅ This is already fixed.

## Verification Checklist

- [ ] API returns `icon_url` in response (use curl command above)
- [ ] Browser console shows `icon_url` in logged workflow data
- [ ] No CORS errors in console
- [ ] No 404 errors for image URLs in Network tab
- [ ] Next.js config includes CloudFront domain
- [ ] TypeScript types include `icon_url` field

## If Still Not Working

1. Check the browser Network tab for the API request to `/api/v1/app/workflows/`
2. Verify the response includes `icon_url`
3. Check if there are any CORS or CSP errors
4. Verify the Image component is receiving the correct props
5. Check if there's a conditional render preventing the Image from showing

## Contact
If none of these solutions work, please check:
1. Browser console for any errors
2. Network tab for failed requests
3. Provide console logs and error messages for further debugging
