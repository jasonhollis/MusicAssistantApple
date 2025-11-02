# Expected Log Sequence for Successful Account Linking

## Overview
This document describes the expected log sequence when a user successfully links their account through the Alexa app.

## Full OAuth 2.0 Authorization Code Flow

### Step 1: Authorization Request (User clicks "Link Account" in Alexa app)

**Request from Alexa:**
```
GET /authorize?response_type=code&client_id=alexa-music-assistant&redirect_uri=https://pitangui.amazon.com/api/skill/link/ABCD1234&state=xyz123&scope=read
```

**Expected Logs:**
```
[INFO] GET /authorize - Authorization request received
[INFO] Query params: response_type=code, client_id=alexa-music-assistant, redirect_uri=https://pitangui.amazon.com/api/skill/link/ABCD1234, state=xyz123
[INFO] Client ID validated: alexa-music-assistant
[INFO] Redirect URI validated: https://pitangui.amazon.com/api/skill/link/ABCD1234
```

### Step 2: User Authentication (In real implementation, shows login form)

**Current Implementation:**
- Auto-authenticates as "test_user" (no login form yet)
- In production, this would show a login page where user enters credentials

**Expected Logs:**
```
[INFO] User authenticated: test_user
[INFO] User granted access to requested scopes: read
```

### Step 3: Authorization Code Generation

**Server Action:**
- Generates a unique authorization code (valid for 10 minutes)
- Stores code with user ID and client ID for later validation

**Expected Logs:**
```
[INFO] Authorization code generated: abc123def456
[INFO] Authorization code stored: code=abc123def456, user=test_user, client=alexa-music-assistant, expires_at=2024-01-20T10:15:00Z
```

### Step 4: Redirect to Alexa

**Server Action:**
- Redirects user back to Alexa with authorization code

**Expected Logs:**
```
[INFO] Redirecting to: https://pitangui.amazon.com/api/skill/link/ABCD1234?code=abc123def456&state=xyz123
[INFO] HTTP 302 redirect sent
```

**User Experience:**
- Browser automatically redirects to Alexa
- User sees "Account successfully linked!" message in Alexa app

### Step 5: Token Exchange (Alexa exchanges code for tokens)

**Request from Alexa (server-to-server):**
```
POST /token
Content-Type: application/x-www-form-urlencoded
Authorization: Basic YWxleGEtbXVzaWMtYXNzaXN0YW50OltTRUNSRVRd

grant_type=authorization_code&code=abc123def456&redirect_uri=https://pitangui.amazon.com/api/skill/link/ABCD1234
```

**Expected Logs:**
```
[INFO] POST /token - Token exchange request received
[INFO] Grant type: authorization_code
[INFO] Client credentials validated: alexa-music-assistant (via Basic Auth)
[INFO] Authorization code validated: abc123def456
[INFO] Authorization code matched: user=test_user, client=alexa-music-assistant
[INFO] Authorization code consumed (single use)
```

### Step 6: Token Generation

**Server Action:**
- Generates access token (valid for 1 hour)
- Generates refresh token (valid for 30 days)
- Stores tokens in database/memory

**Expected Logs:**
```
[INFO] Access token generated: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
[INFO] Access token expires at: 2024-01-20T11:00:00Z (3600 seconds)
[INFO] Refresh token generated: rt_abc123def456xyz789
[INFO] Refresh token expires at: 2024-02-19T10:00:00Z (2592000 seconds)
[INFO] Tokens stored: user=test_user, access_token_id=at_12345, refresh_token_id=rt_67890
```

### Step 7: Token Response to Alexa

**Response to Alexa:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "rt_abc123def456xyz789"
}
```

**Expected Logs:**
```
[INFO] Token response sent successfully
[INFO] HTTP 200 OK
[INFO] Response body: {"access_token":"eyJ...", "token_type":"Bearer", "expires_in":3600, "refresh_token":"rt_abc..."}
```

### Step 8: Account Linking Complete

**Alexa Action:**
- Stores access token and refresh token
- Marks account as linked in Alexa backend
- Shows success message to user

**Expected Logs:**
```
[INFO] Account linking completed successfully for user: test_user
[INFO] Client: alexa-music-assistant
```

---

## Complete Success Log Example

```
2024-01-20 10:00:00 [INFO] GET /authorize - Authorization request received
2024-01-20 10:00:00 [INFO] Query params: response_type=code, client_id=alexa-music-assistant, redirect_uri=https://pitangui.amazon.com/api/skill/link/ABCD1234, state=xyz123
2024-01-20 10:00:00 [INFO] Client ID validated: alexa-music-assistant
2024-01-20 10:00:00 [INFO] Redirect URI validated: https://pitangui.amazon.com/api/skill/link/ABCD1234
2024-01-20 10:00:00 [INFO] User authenticated: test_user
2024-01-20 10:00:00 [INFO] User granted access to requested scopes: read
2024-01-20 10:00:00 [INFO] Authorization code generated: abc123def456
2024-01-20 10:00:00 [INFO] Authorization code stored: code=abc123def456, user=test_user, client=alexa-music-assistant, expires_at=2024-01-20T10:10:00Z
2024-01-20 10:00:01 [INFO] Redirecting to: https://pitangui.amazon.com/api/skill/link/ABCD1234?code=abc123def456&state=xyz123
2024-01-20 10:00:01 [INFO] HTTP 302 redirect sent
2024-01-20 10:00:02 [INFO] POST /token - Token exchange request received
2024-01-20 10:00:02 [INFO] Grant type: authorization_code
2024-01-20 10:00:02 [INFO] Client credentials validated: alexa-music-assistant
2024-01-20 10:00:02 [INFO] Authorization code validated: abc123def456
2024-01-20 10:00:02 [INFO] Authorization code matched: user=test_user, client=alexa-music-assistant
2024-01-20 10:00:02 [INFO] Authorization code consumed (single use)
2024-01-20 10:00:02 [INFO] Access token generated: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
2024-01-20 10:00:02 [INFO] Access token expires at: 2024-01-20T11:00:02Z (3600 seconds)
2024-01-20 10:00:02 [INFO] Refresh token generated: rt_abc123def456xyz789
2024-01-20 10:00:02 [INFO] Refresh token expires at: 2024-02-19T10:00:02Z (2592000 seconds)
2024-01-20 10:00:02 [INFO] Tokens stored: user=test_user
2024-01-20 10:00:02 [INFO] Token response sent successfully
2024-01-20 10:00:02 [INFO] HTTP 200 OK
2024-01-20 10:00:02 [INFO] Account linking completed successfully for user: test_user
```

---

## Common Error Patterns

### Error 1: Invalid Client ID
```
[ERROR] GET /authorize - Invalid client_id: wrong-client-id
[ERROR] HTTP 400 Bad Request
[ERROR] Response: {"error":"invalid_client","error_description":"Client ID not recognized"}
```

**Cause:** Alexa skill configured with wrong Client ID
**Fix:** Verify Client ID in Alexa Developer Console matches "alexa-music-assistant"

### Error 2: Invalid Redirect URI
```
[ERROR] GET /authorize - Invalid redirect_uri: https://wrong-domain.com/callback
[ERROR] HTTP 400 Bad Request
[ERROR] Response: {"error":"invalid_request","error_description":"Redirect URI not whitelisted"}
```

**Cause:** Redirect URI from Alexa doesn't match configured value
**Fix:** Ensure redirect URI in Alexa skill configuration is whitelisted in OAuth server

### Error 3: Invalid Authorization Code
```
[ERROR] POST /token - Invalid authorization code: xyz789
[ERROR] HTTP 400 Bad Request
[ERROR] Response: {"error":"invalid_grant","error_description":"Authorization code not found or expired"}
```

**Cause:** Code expired (>10 minutes old) or already used
**Fix:** User must re-initiate account linking to get new code

### Error 4: Invalid Client Credentials (Token Exchange)
```
[ERROR] POST /token - Client authentication failed
[ERROR] HTTP 401 Unauthorized
[ERROR] Response: {"error":"invalid_client","error_description":"Client authentication failed"}
```

**Cause:** Wrong Client Secret in Basic Auth header
**Fix:** Verify Client Secret in Alexa Developer Console

### Error 5: Missing/Invalid Grant Type
```
[ERROR] POST /token - Invalid grant_type: invalid_type
[ERROR] HTTP 400 Bad Request
[ERROR] Response: {"error":"unsupported_grant_type","error_description":"Grant type must be 'authorization_code'"}
```

**Cause:** Wrong grant type parameter
**Fix:** Ensure Alexa sends grant_type=authorization_code

---

## Timing Expectations

| Step | Expected Duration | Notes |
|------|-------------------|-------|
| Authorization request → Code generation | < 100ms | Instant server-side validation |
| Code generation → Redirect | < 50ms | Immediate redirect |
| Redirect → Token exchange | 1-3 seconds | User browser redirect time + Alexa processing |
| Token exchange → Token generation | < 100ms | Server-side validation and generation |
| Token response → Account linked | 1-2 seconds | Alexa processes and stores tokens |
| **Total flow duration** | **3-6 seconds** | End-to-end user experience |

---

## Validation Checklist

After seeing the expected log sequence, verify:

- [ ] Authorization request received with correct client_id
- [ ] Authorization code generated (16+ character random string)
- [ ] Redirect sent to correct Alexa redirect_uri
- [ ] Token exchange request received within 10 minutes
- [ ] Client credentials validated (Basic Auth)
- [ ] Authorization code validated and consumed
- [ ] Access token generated (JWT or opaque string)
- [ ] Refresh token generated
- [ ] Token response sent with HTTP 200
- [ ] No errors logged during flow
