# Alexa OAuth Endpoints Contract
**Purpose**: Define stable OAuth API contract for Alexa account linking
**Audience**: Developers, Integration Engineers
**Layer**: 03_INTERFACES (API contracts and boundaries)
**Related**:
- [Alexa Authentication Strategic Analysis](../00_ARCHITECTURE/ALEXA_AUTHENTICATION_STRATEGIC_ANALYSIS.md)
- [Alexa OAuth Setup Progress](../05_OPERATIONS/ALEXA_OAUTH_SETUP_PROGRESS.md)

**Last Updated**: 2025-10-25

---

## Intent

This document defines the stable OAuth 2.0 API contract for Music Assistant's Alexa integration. These endpoints form the boundary between Amazon Alexa's account linking service and Music Assistant's authentication system. The contract ensures compatibility with Amazon's OAuth requirements while maintaining implementation flexibility.

---

## Core Principles

**Stability Over Implementation**: This contract defines what endpoints must do, not how they do it.

**OAuth 2.0 Compliance**: All endpoints follow OAuth 2.0 authorization code grant flow as required by Amazon Alexa.

**Backward Compatibility**: Once published, endpoint signatures and core behavior cannot change without versioning.

**Security First**: All endpoints enforce HTTPS in production, support secure parameter handling, and protect against common OAuth vulnerabilities.

---

## Base URL

**Production**: `https://[domain]/alexa/` (exact domain depends on infrastructure choice)

**Local Development**: `http://localhost:8096/alexa/`

**Current Implementation**: `http://192.168.130.11:8096/alexa/` (not publicly accessible)

**Note**: Base URL will change based on chosen public exposure method (Nabu Casa, Tailscale Funnel, or other). Contract remains independent of actual domain.

---

## Endpoint 1: Health Check

### Purpose
Verify OAuth server availability and list available endpoints.

### Specification

**Method**: `GET`

**Path**: `/health`

**Authentication**: None (public endpoint)

**Request Parameters**: None

**Response Format**: JSON

**Success Response** (HTTP 200):
```json
{
  "status": "ok",
  "message": "Music Assistant OAuth Server",
  "endpoints": [
    "/alexa/authorize",
    "/alexa/token",
    "/health"
  ]
}
```

**Error Response** (HTTP 503 Service Unavailable):
```json
{
  "status": "error",
  "message": "OAuth server not ready",
  "endpoints": []
}
```

### Contract Guarantees

- **Always returns JSON** (never HTML or plain text)
- **Status field** indicates server health: `"ok"` or `"error"`
- **Message field** provides human-readable status description
- **Endpoints array** lists all available OAuth endpoints
- **HTTP 200** indicates server is ready to handle OAuth requests
- **HTTP 503** indicates server is starting up or degraded

### Validation Rules

- Response must be valid JSON
- `status` field must be present and either `"ok"` or `"error"`
- `endpoints` array must contain at least `["/alexa/authorize", "/alexa/token", "/health"]` when status is `"ok"`

### Example Request

```bash
curl -X GET https://[domain]/health
```

### Current Implementation

**Status**: WORKING ✅

**Verified Response**:
```json
{
  "status": "ok",
  "message": "Music Assistant OAuth Server",
  "endpoints": [
    "/alexa/authorize",
    "/alexa/token",
    "/health"
  ]
}
```

---

## Endpoint 2: Authorization

### Purpose
Handle OAuth 2.0 authorization requests from Amazon Alexa. Initiates the account linking flow by presenting user authentication interface.

### Specification

**Method**: `GET`

**Path**: `/alexa/authorize`

**Authentication**: User authentication required (redirects to login if not authenticated)

**Query Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `client_id` | string | Yes | OAuth client identifier from Alexa skill configuration |
| `redirect_uri` | string | Yes | Amazon's callback URL where authorization code will be sent |
| `state` | string | Yes | Opaque value from Alexa, must be returned unchanged |
| `response_type` | string | Yes | Must be `"code"` (OAuth authorization code grant) |
| `scope` | string | No | Space-delimited list of permission scopes |

**Response Types**:

**1. User Not Authenticated** (HTTP 302 Redirect):
```
Location: /login?return_to=/alexa/authorize?client_id=...&redirect_uri=...&state=...
```

**2. User Authenticated, Awaiting Consent** (HTTP 200 HTML):
```html
<!DOCTYPE html>
<html>
<body>
  <h1>Authorize Music Assistant</h1>
  <p>Alexa is requesting access to your Music Assistant account.</p>
  <form method="post" action="/alexa/authorize">
    <input type="hidden" name="client_id" value="...">
    <input type="hidden" name="redirect_uri" value="...">
    <input type="hidden" name="state" value="...">
    <button type="submit">Allow Access</button>
  </form>
</body>
</html>
```

**3. User Grants Consent** (HTTP 302 Redirect):
```
Location: https://alexa.amazon.com/callback?code=[AUTHORIZATION_CODE]&state=[ORIGINAL_STATE]
```

**4. User Denies Consent** (HTTP 302 Redirect):
```
Location: https://alexa.amazon.com/callback?error=access_denied&state=[ORIGINAL_STATE]
```

**5. Invalid Request** (HTTP 400 Bad Request):
```json
{
  "error": "invalid_request",
  "error_description": "Missing required parameter: client_id"
}
```

### Contract Guarantees

- **State preservation**: `state` parameter returned unchanged in all redirects
- **Redirect URI validation**: Only redirects to pre-registered URIs
- **Authorization code uniqueness**: Each code is single-use and expires
- **HTTPS enforcement**: Production implementation rejects HTTP requests
- **CSRF protection**: State parameter prevents cross-site request forgery

### Validation Rules

**Request Validation**:
- `client_id` must match registered OAuth client
- `redirect_uri` must match registered callback URL for client
- `response_type` must be exactly `"code"`
- `state` must be present and non-empty

**Authorization Code Properties**:
- Must be unpredictable (cryptographically random)
- Must expire within 10 minutes
- Must be single-use (invalidated after token exchange)
- Must be bound to client_id and redirect_uri

### Example Request

```bash
# User clicks "Link Account" in Alexa app, redirects to:
GET https://[domain]/alexa/authorize?client_id=music-assistant&redirect_uri=https://alexa.amazon.com/callback&state=abc123&response_type=code
```

### Example Successful Flow

```
1. User clicks "Link Account" in Alexa app
   → GET /alexa/authorize?client_id=...&redirect_uri=...&state=abc123&response_type=code

2. Server checks authentication
   → User not logged in
   → HTTP 302 to /login?return_to=/alexa/authorize?...

3. User logs in to Music Assistant
   → Session cookie set
   → HTTP 302 back to /alexa/authorize?...

4. Server shows consent page
   → HTTP 200 with HTML form

5. User clicks "Allow Access"
   → POST /alexa/authorize with consent

6. Server generates authorization code
   → HTTP 302 to https://alexa.amazon.com/callback?code=xyz789&state=abc123

7. Alexa receives authorization code
   → Proceeds to token exchange
```

### Current Implementation

**Status**: IMPLEMENTED (not yet publicly accessible)

**Known Behaviors**:
- Endpoint exists and responds to requests
- Full authorization flow to be verified after public endpoint setup

---

## Endpoint 3: Token Exchange

### Purpose
Exchange authorization code for access token. Called by Amazon Alexa backend after user completes authorization flow.

### Specification

**Method**: `POST`

**Path**: `/alexa/token`

**Authentication**: HTTP Basic Authentication using OAuth client credentials
- Username: `client_id`
- Password: `client_secret`

**Content-Type**: `application/x-www-form-urlencoded`

**Request Parameters** (form-encoded):

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `grant_type` | string | Yes | Must be `"authorization_code"` for initial exchange |
| `code` | string | Yes (initial) | Authorization code from authorization endpoint |
| `redirect_uri` | string | Yes | Must match redirect_uri from authorization request |
| `client_id` | string | Yes | OAuth client identifier |
| `refresh_token` | string | Yes (refresh) | Refresh token for token refresh grant |

**Success Response** (HTTP 200):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "def502004e9b7c8c...",
  "scope": "playback control"
}
```

**Error Responses**:

**Invalid Authorization Code** (HTTP 400):
```json
{
  "error": "invalid_grant",
  "error_description": "Authorization code is invalid or expired"
}
```

**Invalid Client Credentials** (HTTP 401):
```json
{
  "error": "invalid_client",
  "error_description": "Client authentication failed"
}
```

**Redirect URI Mismatch** (HTTP 400):
```json
{
  "error": "invalid_request",
  "error_description": "Redirect URI does not match authorization request"
}
```

**Server Error** (HTTP 500):
```json
{
  "error": "server_error",
  "error_description": "Internal server error occurred"
}
```

### Contract Guarantees

- **Token uniqueness**: Each access token is unique and unpredictable
- **Token expiration**: Tokens have limited lifetime (`expires_in` seconds)
- **Refresh capability**: Refresh tokens allow getting new access tokens without re-authorization
- **Single-use codes**: Authorization codes invalidated after successful exchange
- **Secure transmission**: HTTPS required in production

### Validation Rules

**Request Validation**:
- `grant_type` must be `"authorization_code"` or `"refresh_token"`
- For authorization code grant:
  - `code` must be valid and not expired
  - `redirect_uri` must match original authorization request
  - `client_id` must match code's client
- For refresh token grant:
  - `refresh_token` must be valid and not revoked
  - `client_id` must match token's client

**Response Token Properties**:
- `access_token`: JWT or opaque token, cryptographically secure
- `token_type`: Must be `"Bearer"`
- `expires_in`: Recommended 3600 seconds (1 hour)
- `refresh_token`: Long-lived token for obtaining new access tokens
- `scope`: Space-delimited list of granted permissions

### Example Request (Authorization Code Grant)

```bash
curl -X POST https://[domain]/alexa/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -u "client_id:client_secret" \
  -d "grant_type=authorization_code" \
  -d "code=xyz789" \
  -d "redirect_uri=https://alexa.amazon.com/callback" \
  -d "client_id=music-assistant"
```

### Example Request (Refresh Token Grant)

```bash
curl -X POST https://[domain]/alexa/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -u "client_id:client_secret" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=def502004e9b7c8c..." \
  -d "client_id=music-assistant"
```

### Current Implementation

**Status**: IMPLEMENTED (not yet publicly accessible)

**Known Behaviors**:
- Endpoint exists and responds to requests
- Token generation logic to be verified after public endpoint setup

---

## OAuth 2.0 Flow Sequence

### Complete Authorization Code Flow

```
1. User initiates account linking in Alexa app
   ↓
2. Alexa redirects to: GET /alexa/authorize
   Parameters: client_id, redirect_uri, state, response_type=code
   ↓
3. Music Assistant authenticates user
   (redirects to login if needed)
   ↓
4. Music Assistant shows consent page
   User approves or denies
   ↓
5. Music Assistant generates authorization code
   Redirects to: redirect_uri?code=xyz&state=abc
   ↓
6. Alexa backend receives authorization code
   ↓
7. Alexa calls: POST /alexa/token
   Parameters: grant_type=authorization_code, code=xyz
   Authentication: HTTP Basic (client_id, client_secret)
   ↓
8. Music Assistant validates code
   Returns: access_token, refresh_token, expires_in
   ↓
9. Alexa stores tokens
   Account linking complete!
   ↓
10. Alexa uses access_token for API calls
   When token expires, uses refresh_token to get new access_token
```

---

## Security Considerations

### Required Security Measures

**HTTPS Only (Production)**:
- All endpoints must use HTTPS in production
- Reject HTTP requests or redirect to HTTPS
- Prevents token interception and MITM attacks

**Authorization Code Protection**:
- Codes must be cryptographically random (min 128 bits entropy)
- Single-use only (invalidate after exchange)
- Short expiration (max 10 minutes)
- Bound to client_id and redirect_uri

**Token Security**:
- Access tokens should be JWT or cryptographically secure random strings
- Refresh tokens must be stored securely (hashed)
- Implement token revocation mechanism
- Rate limit token endpoint to prevent brute force

**Client Authentication**:
- Validate client credentials on token endpoint
- Use HTTP Basic Authentication for client_secret
- Store client_secret securely (hashed)

**Redirect URI Validation**:
- Only redirect to pre-registered URIs
- Exact string match (no pattern matching)
- Prevents authorization code interception

**State Parameter**:
- Required for CSRF protection
- Returned unchanged to client
- Client must validate state matches original request

### Threat Mitigations

| Threat | Mitigation |
|--------|------------|
| Authorization code interception | HTTPS only, short expiration, single-use |
| Token theft | Secure storage, HTTPS only, expiration |
| Client impersonation | Client authentication on token endpoint |
| Redirect URI manipulation | Strict URI validation |
| CSRF attacks | State parameter validation |
| Brute force attacks | Rate limiting on token endpoint |

---

## Versioning and Compatibility

### Current Version
**Version**: 1.0
**Status**: Initial implementation
**Compatibility**: Amazon Alexa OAuth 2.0 account linking

### Backward Compatibility Promise

**Stable Elements** (will not change):
- Endpoint paths (`/alexa/authorize`, `/alexa/token`, `/health`)
- Required query parameters
- Response JSON structure
- OAuth 2.0 flow sequence
- HTTP status codes for success/error cases

**May Change** (with version bump):
- Additional optional parameters
- Additional response fields
- Error message text (not error codes)
- Performance characteristics
- Implementation details

### Deprecation Policy

If breaking changes are required:
1. New endpoints created with version prefix (`/v2/alexa/authorize`)
2. Old endpoints marked deprecated (12-month notice)
3. Old endpoints return deprecation warning in response
4. Old endpoints removed after deprecation period

---

## Testing and Verification

### Health Check Test

```bash
# Expected: HTTP 200, JSON with status "ok"
curl -v https://[domain]/health
```

**Pass Criteria**:
- HTTP 200 status code
- Valid JSON response
- `status` field equals `"ok"`
- `endpoints` array contains all three OAuth endpoints

### Authorization Endpoint Test

```bash
# Expected: Redirect to login or consent page
curl -v "https://[domain]/alexa/authorize?client_id=test&redirect_uri=https://example.com&state=test123&response_type=code"
```

**Pass Criteria**:
- HTTP 200 (consent page) or HTTP 302 (redirect to login)
- If 302, Location header points to valid URL
- State parameter preserved in all redirects

### Token Endpoint Test

```bash
# Expected: HTTP 400 (invalid code) or HTTP 200 (if code valid)
curl -X POST https://[domain]/alexa/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -u "test:test" \
  -d "grant_type=authorization_code&code=invalid&redirect_uri=https://example.com&client_id=test"
```

**Pass Criteria**:
- HTTP 400 with `invalid_grant` error (expected for invalid code)
- Valid JSON error response
- Error response includes `error` and `error_description` fields

### End-to-End Flow Test

**Prerequisites**:
- Alexa skill created in Amazon Developer Console
- Account linking configured with OAuth endpoints
- Test Amazon account

**Test Steps**:
1. Open Alexa app, navigate to skill
2. Click "Link Account"
3. Verify redirect to Music Assistant authorization page
4. Log in to Music Assistant (if needed)
5. Approve consent request
6. Verify redirect back to Alexa app
7. Verify account shows as "Linked" in Alexa app
8. Test skill functionality requiring account access

**Pass Criteria**:
- All redirects work correctly
- No error pages shown
- Account linking completes successfully
- Skill can access Music Assistant via API

---

## Monitoring and Observability

### Key Metrics

**Availability**:
- Health endpoint uptime (target: 99.9%)
- Authorization endpoint response time (target: <500ms)
- Token endpoint response time (target: <200ms)

**Success Rates**:
- Authorization requests completed (target: >95%)
- Token exchanges successful (target: >98%)
- Refresh token grants successful (target: >98%)

**Security Events**:
- Invalid client_id attempts (alert threshold: >10/hour)
- Invalid authorization code attempts (alert threshold: >50/hour)
- Failed token refreshes (alert threshold: >100/hour)

### Logging Requirements

**Authorization Endpoint**:
- Log: `client_id`, `redirect_uri`, `state`, timestamp
- Log: Authentication success/failure
- Log: Consent granted/denied
- Do NOT log: User credentials, authorization codes

**Token Endpoint**:
- Log: `client_id`, `grant_type`, timestamp
- Log: Token generation success/failure
- Log: Invalid code/token attempts
- Do NOT log: `client_secret`, tokens, authorization codes

**Health Endpoint**:
- Log: Request count (aggregate)
- Do NOT log: Individual health check requests (too noisy)

---

## See Also

- **[Alexa Authentication Strategic Analysis](../00_ARCHITECTURE/ALEXA_AUTHENTICATION_STRATEGIC_ANALYSIS.md)** - Architecture principles
- **[Alexa OAuth Setup Progress](../05_OPERATIONS/ALEXA_OAUTH_SETUP_PROGRESS.md)** - Implementation status
- **[Alexa Infrastructure Options](../02_REFERENCE/ALEXA_INFRASTRUCTURE_OPTIONS.md)** - Deployment options
- **[OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)** - OAuth 2.0 specification
- **[Amazon Alexa Account Linking](https://developer.amazon.com/docs/account-linking/understand-account-linking.html)** - Alexa documentation
