# OAuth 2.0 Endpoint Interface Specifications
**Purpose**: API contracts for OAuth authorization and token endpoints
**Audience**: Developers, API consumers, integration engineers
**Layer**: 03_INTERFACES
**Related**: [00_ARCHITECTURE/OAUTH_PRINCIPLES.md](../00_ARCHITECTURE/OAUTH_PRINCIPLES.md), [02_REFERENCE/OAUTH_CONSTANTS.md](../02_REFERENCE/OAUTH_CONSTANTS.md)

## Intent

This document defines the stable API contracts for OAuth 2.0 endpoints. These interfaces must remain backward compatible - implementations may change, but endpoint behavior and response formats are fixed.

## Base URL

```
Production:  https://dev.jasonhollis.com/alexa
Development: http://localhost:8096/alexa
```

All endpoints MUST be served over HTTPS in production (RFC 6749 requirement).

## Endpoint: Authorization Endpoint

### Purpose
Initiates OAuth authorization flow. Displays consent screen to user and issues authorization code upon approval.

### Interface Contract

```
Method:      GET
Path:        /alexa/authorize
Auth:        None (public endpoint)
Content-Type: N/A (query parameters)
Response:    HTML (consent screen) OR 302 Redirect (to redirect_uri)
```

### Request Parameters

| Parameter | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `response_type` | string | Yes | Must be "code" | Only authorization code grant supported |
| `client_id` | string | Yes | OAuth client identifier | Must match registered client |
| `redirect_uri` | string | Yes | Callback URL | Must match pre-registered URI (exact match) |
| `state` | string | Recommended | CSRF token | Min 16 bytes entropy, echo in response |
| `scope` | string | Optional | Requested permissions | Space-separated scope list |
| `code_challenge` | string | Optional* | PKCE challenge | Required for public clients |
| `code_challenge_method` | string | Optional* | PKCE hash method | Must be "S256" if provided |

*PKCE parameters optional for confidential clients, required for public clients (like Alexa)

### Request Example

```http
GET /alexa/authorize?response_type=code&client_id=amazon-alexa&redirect_uri=https%3A%2F%2Fpitangui.amazon.com%2Fauth%2Fo2%2Fcallback&state=xyz123&scope=music.read+music.control&code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&code_challenge_method=S256 HTTP/1.1
Host: dev.jasonhollis.com
User-Agent: Amazon-Alexa/iOS-18.7
Accept: text/html
```

### Response: Consent Screen (HTTP 200)

Returns HTML form for user to approve/deny authorization.

```http
HTTP/1.1 200 OK
Content-Type: text/html; charset=utf-8
Cache-Control: no-store

<!DOCTYPE html>
<html>
  <head><title>Authorize Music Assistant</title></head>
  <body>
    <h1>🎵 Authorize Music Assistant</h1>
    <p>Amazon Alexa is requesting access to your account</p>
    <div class="permissions">
      <h3>This will allow Amazon Alexa to:</h3>
      <ul>
        <li>Read your music library and playlists</li>
        <li>Control playback (play, pause, skip)</li>
      </ul>
    </div>
    <form method="POST" action="/alexa/approve">
      <input type="hidden" name="auth_code" value="[TEMP_AUTH_CODE]">
      <input type="hidden" name="state" value="[STATE]">
      <button type="submit">Approve & Link Account</button>
    </form>
  </body>
</html>
```

### Response: Authorization Approved (HTTP 302)

After user approves, redirect back to client with authorization code.

```http
HTTP/1.1 302 Found
Location: https://pitangui.amazon.com/auth/o2/callback?code=5BXfFUdOyRvcJ5OOza2MRdKiN3fq3tIfLfge_7_h2AQ&state=xyz123
Cache-Control: no-store
```

### Error Responses

All errors redirect to `redirect_uri` with error parameters (except invalid redirect_uri).

**Invalid redirect_uri** (cannot redirect):
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_request",
  "error_description": "redirect_uri does not match registered URIs"
}
```

**User denied authorization**:
```http
HTTP/1.1 302 Found
Location: https://pitangui.amazon.com/auth/o2/callback?error=access_denied&error_description=User+denied+authorization&state=xyz123
```

**Invalid client**:
```http
HTTP/1.1 302 Found
Location: https://pitangui.amazon.com/auth/o2/callback?error=unauthorized_client&error_description=Client+not+registered&state=xyz123
```

### Contract Guarantees

1. **Idempotency**: Multiple identical requests generate different authorization codes (not idempotent by design)
2. **State Echo**: `state` parameter always echoed in redirect (if provided)
3. **Code Lifetime**: Authorization codes valid for exactly 5 minutes
4. **Single-Use**: Each authorization code can be exchanged once
5. **Binding**: Code binds client_id, redirect_uri, code_challenge, scope

---

## Endpoint: Consent Approval Handler

### Purpose
Handles form submission when user approves authorization. Internal endpoint called by consent screen.

### Interface Contract

```
Method:      POST
Path:        /alexa/approve
Auth:        None (validates temporary auth code)
Content-Type: application/x-www-form-urlencoded
Response:    302 Redirect (to redirect_uri with authorization code)
```

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `auth_code` | string | Yes | Temporary authorization code from consent screen |
| `state` | string | Yes | CSRF token (must match original request) |

### Request Example

```http
POST /alexa/approve HTTP/1.1
Host: dev.jasonhollis.com
Content-Type: application/x-www-form-urlencoded
Content-Length: 89

auth_code=temp_abc123&state=xyz123
```

### Success Response

```http
HTTP/1.1 302 Found
Location: https://pitangui.amazon.com/auth/o2/callback?code=5BXfFUdOyRvcJ5OOza2MRdKiN3fq3tIfLfge_7_h2AQ&state=xyz123
Cache-Control: no-store
```

### Error Responses

**CSRF validation failed**:
```http
HTTP/1.1 400 Bad Request
Content-Type: text/html

<!DOCTYPE html>
<html>
  <body>
    <h1>⚠️ Authorization Failed</h1>
    <p>CSRF validation failed: state parameter mismatch</p>
  </body>
</html>
```

### Contract Guarantees

1. **State Validation**: State parameter must match temporary auth code metadata
2. **Expiration**: Temporary auth codes expire in 5 minutes
3. **Atomic**: Authorization code generation and redirect are atomic
4. **Final Redirect**: Always produces final authorization code (not temporary)

---

## Endpoint: Token Endpoint

### Purpose
Exchanges authorization code for access/refresh tokens OR refreshes access token.

### Interface Contract

```
Method:      POST
Path:        /alexa/token
Auth:        Client credentials (via POST body OR HTTP Basic Auth)
Content-Type: application/x-www-form-urlencoded
Response:    JSON (token response)
```

### Grant Type: authorization_code

Exchanges authorization code for tokens.

#### Request Parameters

| Parameter | Type | Required | Description | Constraints |
|-----------|------|----------|-------------|-------------|
| `grant_type` | string | Yes | Must be "authorization_code" | Fixed value |
| `code` | string | Yes | Authorization code | From /authorize endpoint |
| `redirect_uri` | string | Yes | Callback URL | Must match authorization request |
| `client_id` | string | Yes | OAuth client identifier | Must match registered client |
| `client_secret` | string | No* | Client secret | Required for confidential clients |
| `code_verifier` | string | No** | PKCE verifier | Required for PKCE-enabled requests |

*Required for confidential clients, omitted for public clients (PKCE instead)
**Required if `code_challenge` was provided in authorization request

#### Request Example (Public Client with PKCE)

```http
POST /alexa/token HTTP/1.1
Host: dev.jasonhollis.com
Content-Type: application/x-www-form-urlencoded
Content-Length: 234

grant_type=authorization_code&code=5BXfFUdOyRvcJ5OOza2MRdKiN3fq3tIfLfge_7_h2AQ&redirect_uri=https%3A%2F%2Fpitangui.amazon.com%2Fauth%2Fo2%2Fcallback&client_id=amazon-alexa&code_verifier=dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk
```

#### Request Example (Confidential Client with client_secret)

```http
POST /alexa/token HTTP/1.1
Host: dev.jasonhollis.com
Content-Type: application/x-www-form-urlencoded
Authorization: Basic YW1hem9uLWFsZXhhOk52OFhoLXpHX3dSM21LMnBMNGpGOXFZNmJUNXZDMXhEMHNXN2FN
Content-Length: 198

grant_type=authorization_code&code=5BXfFUdOyRvcJ5OOza2MRdKiN3fq3tIfLfge_7_h2AQ&redirect_uri=https%3A%2F%2Fpitangui.amazon.com%2Fauth%2Fo2%2Fcallback&client_id=amazon-alexa
```

#### Success Response

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: no-store
Pragma: no-cache

{
  "access_token": "fDpnBe_wSfmkJebHQkfMfKzfN_AeFXMcYQxow40eusE",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "hHBMuKyImOepseExdJrYeaTLfIZlhdOiYNSJdq2q1LM",
  "scope": "music.read music.control"
}
```

### Grant Type: refresh_token

Refreshes access token using refresh token.

#### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `grant_type` | string | Yes | Must be "refresh_token" |
| `refresh_token` | string | Yes | Previously issued refresh token |
| `client_id` | string | Yes | OAuth client identifier |
| `client_secret` | string | No* | Client secret |
| `scope` | string | Optional | Requested scope (must be subset of original) |

*Required for confidential clients, omitted for public clients

#### Request Example

```http
POST /alexa/token HTTP/1.1
Host: dev.jasonhollis.com
Content-Type: application/x-www-form-urlencoded
Content-Length: 124

grant_type=refresh_token&refresh_token=hHBMuKyImOepseExdJrYeaTLfIZlhdOiYNSJdq2q1LM&client_id=amazon-alexa
```

#### Success Response

```http
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: no-store
Pragma: no-cache

{
  "access_token": "t0CPn3AjNoh1LtXwQ0nYoq3-YHQZH97iQHYFAiZvDxc",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "hHBMuKyImOepseExdJrYeaTLfIZlhdOiYNSJdq2q1LM",
  "scope": "music.read music.control"
}
```

### Error Responses

**Invalid authorization code**:
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_grant",
  "error_description": "Authorization code not found or already used"
}
```

**Authorization code expired**:
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_grant",
  "error_description": "Authorization code has expired"
}
```

**PKCE validation failed**:
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_grant",
  "error_description": "PKCE verification failed: code_verifier does not match code_challenge"
}
```

**Invalid client credentials**:
```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json
WWW-Authenticate: Basic realm="OAuth Token Endpoint"

{
  "error": "invalid_client",
  "error_description": "Client authentication failed"
}
```

**redirect_uri mismatch**:
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_grant",
  "error_description": "redirect_uri does not match authorization request"
}
```

**Invalid refresh token**:
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "invalid_grant",
  "error_description": "Refresh token not found or invalid"
}
```

### Contract Guarantees

1. **Atomicity**: Token generation and code invalidation are atomic
2. **Idempotency**: Duplicate requests with same code fail (already used)
3. **Validation Order**: Client auth → code validation → PKCE validation
4. **Token Format**: Tokens always 43 characters (URL-safe base64)
5. **Cache Headers**: Responses always include `Cache-Control: no-store`

---

## Endpoint: Health Check (Non-OAuth)

### Purpose
Verify OAuth server is running and responsive.

### Interface Contract

```
Method:      GET
Path:        /health
Auth:        None (public endpoint)
Response:    JSON (health status)
```

### Request Example

```http
GET /health HTTP/1.1
Host: dev.jasonhollis.com
Accept: application/json
```

### Success Response

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "ok",
  "message": "Music Assistant OAuth Server",
  "endpoints": ["/alexa/authorize", "/alexa/token", "/health"]
}
```

### Contract Guarantees

1. **Always 200**: Returns 200 OK if server is running
2. **Simple Check**: Does not validate database or dependencies
3. **Fast**: Returns immediately (no I/O operations)

---

## HTTP Basic Authentication

Confidential clients MAY send credentials via HTTP Basic Auth instead of POST body.

### Format

```
Header: Authorization: Basic [BASE64(client_id:client_secret)]

Example:
client_id = amazon-alexa
client_secret = Nv8Xh-zG_wR3mK2pL4jF9qY6bT5vC1xD0sW7aM
Combined = amazon-alexa:Nv8Xh-zG_wR3mK2pL4jF9qY6bT5vC1xD0sW7aM
Base64 = YW1hem9uLWFsZXhhOk52OFhoLXpHX3dSM21LMnBMNGpGOXFZNmJUNXZDMXhEMHNXN2FN

Header: Authorization: Basic YW1hem9uLWFsZXhhOk52OFhoLXpHX3dSM21LMnBMNGpGOXFZNmJUNXZDMXhEMHNXN2FN
```

### Contract Guarantees

1. **Equivalence**: Basic Auth equivalent to POST body credentials
2. **Priority**: If both provided, Basic Auth takes precedence
3. **Encoding**: Standard base64 encoding (RFC 2617)

---

## Data Types

### Token Response Object

```typescript
interface TokenResponse {
  access_token: string;    // URL-safe base64, 43 chars
  token_type: "Bearer";    // Always "Bearer" (RFC 6750)
  expires_in: number;      // Seconds until expiration (3600)
  refresh_token?: string;  // URL-safe base64, 43 chars (optional for refresh grant)
  scope?: string;          // Space-separated scope list (optional)
}
```

### Error Response Object

```typescript
interface ErrorResponse {
  error: string;              // OAuth error code (see RFC 6749)
  error_description?: string; // Human-readable description
  error_uri?: string;         // URL to error documentation (optional)
}
```

---

## Versioning Policy

### Current Version
```
Version: 1.0
Status: Stable
Breaking Changes: None planned
```

### Compatibility Guarantees

**Will NOT Change** (backward compatible):
- Endpoint paths (`/alexa/authorize`, `/alexa/token`)
- Required parameters
- Response JSON structure
- Error code meanings
- Token format (base64url, 43 chars)
- HTTP methods (GET for authorize, POST for token)

**MAY Change** (forward compatible):
- Optional parameters (new optional parameters may be added)
- Response fields (new fields may be added to JSON)
- Error descriptions (text may be clarified)
- HTTP headers (new headers may be added)

**Deprecation Policy**:
- 90-day notice before removing any feature
- Deprecated features continue working during deprecation period
- Clients updated to use new endpoints before removal

---

## Security Requirements

### Transport Security

**MUST**:
- Serve all endpoints over HTTPS (TLS 1.2+) in production
- Use valid TLS certificates (not self-signed)
- Enable HTTP Strict Transport Security (HSTS)

**MUST NOT**:
- Serve OAuth endpoints over HTTP in production
- Accept invalid or expired TLS certificates
- Allow TLS <1.2 (SSL 2.0, SSL 3.0, TLS 1.0, TLS 1.1 are insecure)

### Request Validation

**MUST**:
- Validate all required parameters present
- Validate parameter types and formats
- Validate redirect_uri exact match (no substring/pattern matching)
- Validate code_challenge_method is "S256" (not "plain")
- Validate authorization code not expired
- Validate authorization code single-use
- Validate PKCE code_verifier matches code_challenge

**MUST NOT**:
- Trust client-provided data without validation
- Skip PKCE validation for public clients
- Allow wildcard redirect URIs
- Allow HTTP redirect URIs in production

### Response Security

**MUST**:
- Include `Cache-Control: no-store` on token responses
- Include `Pragma: no-cache` on token responses
- Use cryptographically secure random for tokens (256+ bits entropy)
- Return generic error messages (no sensitive details)

**MUST NOT**:
- Include tokens in URLs (use POST body or headers)
- Cache token responses
- Log tokens in plain text
- Return stack traces or internal errors to clients

---

## Testing Contracts

### Test Vectors for PKCE

**Code Verifier**:
```
dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk
```

**Code Challenge** (SHA-256 of verifier):
```
E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
```

**Validation**:
```python
import hashlib
import base64

verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
expected_challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

digest = hashlib.sha256(verifier.encode()).digest()
computed_challenge = base64.urlsafe_b64encode(digest).decode().rstrip('=')

assert computed_challenge == expected_challenge  # Should pass
```

---

## See Also

- **[00_ARCHITECTURE/OAUTH_PRINCIPLES.md](../00_ARCHITECTURE/OAUTH_PRINCIPLES.md)** - OAuth architectural principles
- **[01_USE_CASES/ALEXA_ACCOUNT_LINKING.md](../01_USE_CASES/ALEXA_ACCOUNT_LINKING.md)** - User workflows
- **[02_REFERENCE/OAUTH_CONSTANTS.md](../02_REFERENCE/OAUTH_CONSTANTS.md)** - Token formats and constants
- **[04_INFRASTRUCTURE/OAUTH_IMPLEMENTATION.md](../04_INFRASTRUCTURE/OAUTH_IMPLEMENTATION.md)** - Implementation details
- **[05_OPERATIONS/OAUTH_TESTING.md](../05_OPERATIONS/OAUTH_TESTING.md)** - Testing procedures
