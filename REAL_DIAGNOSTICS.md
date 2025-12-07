# REAL ISSUE DIAGNOSTICS - Knowledge Graph Not Working

## Current State
- ✅ Backend API: Confirmed working (all 24 endpoints)
- ✅ Frontend: Running on port 8080
- ❌ Frontend → Backend Communication: BROKEN

## What User Reported
1. Element creation: Not working
2. Lesson creation: Not working  
3. Graph manipulation: Not working

## Root Cause Investigation Needed

### STEP 1: Check Frontend Environment
Frontend needs to know where Backend is:
- Frontend URL: http://localhost:8080
- Backend URL: http://localhost:8000

Check: `frontend/.env` or `frontend/.env.local`
- VITE_DJANGO_API_URL should be set
- VITE_WEBSOCKET_URL should be set

### STEP 2: Check API Client Configuration
File: `frontend/src/integrations/api/config.ts`
- Does it use VITE_DJANGO_API_URL env variable?
- Does it default to http://localhost:8000/api if not set?

### STEP 3: Check Authentication
When trying to create element:
1. Is user authenticated (has token)?
2. Is token being sent in Authorization header?
3. Check if useAuth() returns valid user

### STEP 4: Check Network Requests
In browser DevTools → Network tab:
1. When clicking "Create Element":
   - Is POST request being made to `/api/knowledge-graph/elements/`?
   - What's the response status? (Should be 201)
   - What's the response body? (Error message if failed)

### STEP 5: Check Console Errors
In browser DevTools → Console:
1. Are there JavaScript errors?
2. Are there CORS errors?
3. Are there TypeError about API calls?

### STEP 6: Check Form Submission
In ContentCreatorPage.tsx:
- Is handleElementSubmit being called?
- Is data being sent to API?
- Or is form validation blocking submission?

## Common Issues

### Issue A: Frontend doesn't know backend URL
Fix: Set VITE_DJANGO_API_URL in `.env.local`
```
VITE_DJANGO_API_URL=http://localhost:8000/api
```

### Issue B: CORS issues
If getting CORS error:
- Backend CORS is configured in settings.py
- But Frontend must be whitelisted
- Check: CORS_ALLOWED_ORIGINS in settings.py

### Issue C: Authentication not working
If getting 401 Unauthorized:
- Token not being sent
- Token expired
- User not authenticated

### Issue D: Form not submitting
If form doesn't submit:
- Validation errors not shown
- Button not clickable
- Event handler not attached

### Issue E: Wrong API paths
If getting 404:
- Frontend calling wrong endpoint
- Backend endpoint not registered
- Check URL in contentCreatorService.ts

## How to Debug

### In Browser Console:
```javascript
// Check if API client works
import { apiClient } from '@/integrations/api/apiClient'
apiClient.get('/knowledge-graph/elements/').then(r => console.log(r))

// Check if user is authenticated
import { useAuth } from '@/hooks/useAuth'
// In component context, check useAuth()
```

### Check Network Tab:
1. Open DevTools (F12)
2. Go to Network tab
3. Create an element
4. Look for POST to `/api/knowledge-graph/elements/`
5. Click it and check:
   - Request headers (Authorization token?)
   - Response status (200? 400? 401? 404? 500?)
   - Response body (error message?)

### Check Frontend Logs:
1. Open browser console (F12)
2. Look for red errors
3. Look for yellow warnings
4. Check for CORS errors

## What To Report Back

Please provide:
1. **Network Tab Screenshot**: When creating element, what does the POST request show?
2. **Console Errors**: Any red errors in console?
3. **Response Body**: What error message if any?
4. **Response Status**: 404? 401? 400? 500?
5. **Frontend .env**: What are VITE_DJANGO_API_URL and VITE_WEBSOCKET_URL set to?

## Next Steps

Once we know WHICH step is failing, we can fix it:
- If frontend doesn't know backend → Set .env
- If CORS → Update settings.py
- If auth → Fix token handling
- If form → Debug form submission
- If API paths → Check services
