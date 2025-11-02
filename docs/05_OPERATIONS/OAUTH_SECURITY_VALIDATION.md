# OAuth Server Security Validation Procedures

**Layer**: 05 - Operations
**Date**: 2025-10-26
**Purpose**: Security testing and validation procedures for OAuth server deployment

## Intent

This document provides security-focused test procedures to validate the OAuth server is functioning correctly and securely before production use. These tests verify client validation, PKCE implementation, and proper error handling.

## Prerequisites

- OAuth server running on port 8096
- Health check endpoint responding (see OAUTH_SERVER_STARTUP.md)
- curl command available for testing
- Ability to parse JSON responses

## Security Test Suite

### Test 1: Valid Client Authentication

**Purpose**: Verify that valid client credentials are accepted

```bash
curl -i 'http://192.168.130.147:8096/alexa/authorize?response_type=code&client_id=amazon-alexa&redirect_uri=https://pitangui.amazon.com/auth/o2/callback&state=test123&code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&code_challenge_method=S256'
```

**Expected Response**:
- HTTP Status: `302 Found` (redirect)
- Location header contains: `code=<authorization_code>`
- State parameter echoed back: `state=test123`

**Security Check**:
- ✅ Server accepts valid client_id
- ✅ Generates authorization code (32 bytes minimum)
- ✅ Code is cryptographically random

---

### Test 2: Invalid Client ID Rejection

**Purpose**: Verify that invalid client IDs are rejected

```bash
curl -i 'http://192.168.130.147:8096/alexa/authorize?response_type=code&client_id=INVALID&redirect_uri=http://localhost&state=test&code_challenge=abc&code_challenge_method=S256'
```

**Expected Response**:
- HTTP Status: `400 Bad Request` (NOT 302)
- Error message in response: "Invalid client" or "Client authentication failed"
- NO authorization code generated

**Security Check**:
- ✅ Server rejects unknown client_id
- ✅ Does not leak information about valid clients
- ✅ Returns appropriate error status

---

### Test 3: Missing Required Parameters

**Purpose**: Verify that incomplete requests are rejected

```bash
# Test: Missing response_type
curl -i 'http://192.168.130.147:8096/alexa/authorize?client_id=amazon-alexa&redirect_uri=http://localhost&state=test&code_challenge=abc&code_challenge_method=S256'

# Test: Missing code_challenge
curl -i 'http://192.168.130.147:8096/alexa/authorize?response_type=code&client_id=amazon-alexa&redirect_uri=http://localhost&state=test&code_challenge_method=S256'

# Test: Missing state parameter
curl -i 'http://192.168.130.147:8096/alexa/authorize?response_type=code&client_id=amazon-alexa&redirect_uri=http://localhost&code_challenge=abc&code_challenge_method=S256'
```

**Expected Response for All**:
- HTTP Status: `400 Bad Request`
- Error message: "Missing required parameter: [param_name]"
- NO authorization code generated

**Security Check**:
- ✅ Server enforces all required parameters
- ✅ Prevents incomplete OAuth flows
- ✅ Returns clear error messages

---

### Test 4: SQL Injection Prevention

**Purpose**: Verify that SQL injection attempts are safely handled

```bash
curl -i "http://192.168.130.147:8096/alexa/authorize?response_type=code&client_id=amazon-alexa'; DROP TABLE users;--&redirect_uri=http://localhost&state=test&code_challenge=abc&code_challenge_method=S256"
```

**Expected Response**:
- HTTP Status: `400 Bad Request` (client_id validation fails)
- NO database operations performed
- Application remains running and responsive

**Security Check**:
- ✅ Invalid client_id format rejected
- ✅ SQL injection payload neutralized
- ✅ Server continues operating normally

---

### Test 5: XSS Prevention in Redirect

**Purpose**: Verify that redirect URIs are properly validated

```bash
# Test: Redirect URI with JavaScript payload
curl -i 'http://192.168.130.147:8096/alexa/authorize?response_type=code&client_id=amazon-alexa&redirect_uri=javascript:alert(1)&state=test&code_challenge=abc&code_challenge_method=S256'
```

**Expected Response**:
- HTTP Status: `400 Bad Request`
- Error message: "Invalid redirect_uri"
- NO redirect to malicious URI

**Security Check**:
- ✅ Redirect URI validated against whitelist
- ✅ No reflection of user input in response
- ✅ XSS payloads rejected

---

### Test 6: PKCE Implementation Validation

**Purpose**: Verify PKCE (Proof Key for Code Exchange) is correctly implemented

#### Step 1: Generate Valid PKCE Pair

```bash
python3 << 'EOF'
import base64
import hashlib
import secrets

# Generate code_verifier (32 bytes, URL-safe base64, no padding)
code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')
print(f"code_verifier: {code_verifier}")

# Generate code_challenge (SHA256 of verifier, URL-safe base64, no padding)
code_challenge = base64.urlsafe_b64encode(
    hashlib.sha256(code_verifier.encode()).digest()
).decode().rstrip('=')
print(f"code_challenge: {code_challenge}")
print(f"code_challenge_method: S256")
EOF
```

#### Step 2: Get Authorization Code

```bash
# Use the generated code_challenge and code_verifier
curl -i "http://192.168.130.147:8096/alexa/authorize?response_type=code&client_id=amazon-alexa&redirect_uri=https://pitangui.amazon.com/auth/o2/callback&state=test&code_challenge=<GENERATED_CHALLENGE>&code_challenge_method=S256"

# Extract authorization code from Location header
# Save for Step 3
```

#### Step 3: Exchange Code with Valid PKCE Verifier

```bash
curl -X POST -i http://192.168.130.147:8096/alexa/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=<AUTH_CODE>&client_id=amazon-alexa&client_secret=<CLIENT_SECRET>&code_verifier=<CODE_VERIFIER>&redirect_uri=https://pitangui.amazon.com/auth/o2/callback"
```

**Expected Response**:
- HTTP Status: `200 OK`
- Response contains: `access_token`, `refresh_token`, `expires_in`, `token_type`

**Security Check**:
- ✅ PKCE verifier validated against original challenge
- ✅ Access token issued only with valid PKCE
- ✅ Tokens are cryptographically random

---

### Test 7: PKCE Verification Failure

**Purpose**: Verify that mismatched PKCE verifiers are rejected

```bash
# Use authorization code from Test 6, but WRONG code_verifier
WRONG_VERIFIER=$(python3 -c "import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('='))")

curl -X POST -i http://192.168.130.147:8096/alexa/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=<AUTH_CODE>&client_id=amazon-alexa&client_secret=<CLIENT_SECRET>&code_verifier=$WRONG_VERIFIER&redirect_uri=https://pitangui.amazon.com/auth/o2/callback"
```

**Expected Response**:
- HTTP Status: `400 Bad Request`
- Error message: "PKCE verification failed" or "Invalid code_verifier"
- NO access token issued

**Security Check**:
- ✅ PKCE mismatch detected
- ✅ Token NOT issued with wrong verifier
- ✅ Authorization code remains valid for legitimate retry

---

### Test 8: Authorization Code Expiration

**Purpose**: Verify that authorization codes expire after 5 minutes

```bash
# Get authorization code (from Test 6 Step 2)
AUTH_CODE=<code_from_test_6>

# Immediately try to exchange (should succeed)
curl -X POST -i http://192.168.130.147:8096/alexa/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=$AUTH_CODE&client_id=amazon-alexa&client_secret=<CLIENT_SECRET>&code_verifier=<VERIFIER>&redirect_uri=https://pitangui.amazon.com/auth/o2/callback"
```

**Expected Response**:
- HTTP Status: `200 OK` (code is valid immediately)
- Access token issued

**Then after 5+ minutes**:
```bash
# Try same exchange again (should fail)
curl -X POST -i http://192.168.130.147:8096/alexa/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=$AUTH_CODE&client_id=amazon-alexa&client_secret=<CLIENT_SECRET>&code_verifier=<VERIFIER>&redirect_uri=https://pitangui.amazon.com/auth/o2/callback"
```

**Expected Response**:
- HTTP Status: `400 Bad Request`
- Error message: "Authorization code expired" or "Invalid code"
- NO access token issued

**Security Check**:
- ✅ Codes valid immediately after generation
- ✅ Codes expire within 5 minutes
- ✅ Expired codes cannot be reused

---

### Test 9: Token Payload Validation

**Purpose**: Verify that issued tokens are valid and properly formatted

```bash
curl -X POST http://192.168.130.147:8096/alexa/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=<AUTH_CODE>&client_id=amazon-alexa&client_secret=<CLIENT_SECRET>&code_verifier=<VERIFIER>&redirect_uri=https://pitangui.amazon.com/auth/o2/callback" | jq .
```

**Expected Response Format**:
```json
{
  "access_token": "<32-byte-random-string>",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "<32-byte-random-string>",
  "scope": "music.read music.control"
}
```

**Security Check**:
- ✅ access_token is present and non-empty
- ✅ token_type is "Bearer"
- ✅ expires_in is 3600 (1 hour)
- ✅ refresh_token is present and different from access_token
- ✅ scope matches requested scopes

---

## Security Test Checklist

After completing all tests above, verify:

- [ ] Test 1: Valid client accepted
- [ ] Test 2: Invalid client rejected
- [ ] Test 3: Missing parameters rejected
- [ ] Test 4: SQL injection neutralized
- [ ] Test 5: XSS in redirect rejected
- [ ] Test 6: Valid PKCE verifier accepted
- [ ] Test 7: Invalid PKCE verifier rejected
- [ ] Test 8: Authorization code expiration working
- [ ] Test 9: Token format correct and valid

## Security Issues Found

If any test fails:

1. **Document the failure**: Note test number, input, expected vs actual response
2. **Stop deployment**: Do not expose to public internet until resolved
3. **Diagnose**: Check OAuth server logs (`/data/start_oauth_server.log`)
4. **Fix**: Correct implementation in Layer 04 code
5. **Retest**: Re-run all security tests after fix

## Production Deployment Gates

Before exposing OAuth server to public internet:

- [ ] All 9 security tests passing
- [ ] Authorization code expiration verified
- [ ] PKCE validation working correctly
- [ ] Invalid inputs properly rejected
- [ ] Client credentials validated
- [ ] No sensitive errors leaked in responses
- [ ] Server handles malformed requests gracefully
- [ ] Performance acceptable under load (if applicable)

## See Also

- `docs/05_OPERATIONS/OAUTH_SERVER_STARTUP.md` - Server startup procedures
- `docs/04_INFRASTRUCTURE/OAUTH_SERVER_IMPLEMENTATION.md` - Implementation details
- `docs/03_INTERFACES/ALEXA_OAUTH_ENDPOINTS_CONTRACT.md` - Endpoint specifications
