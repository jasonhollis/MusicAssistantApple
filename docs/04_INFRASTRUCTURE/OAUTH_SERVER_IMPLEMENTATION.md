# OAuth Server Implementation - Music Assistant Alexa Integration

**Layer**: 04 - Infrastructure
**Date**: 2025-10-26
**Status**: ✅ Complete and Tested

## Overview

Standalone OAuth 2.0 Authorization Server for Music Assistant Alexa Skill account linking. Implements RFC 6749 (OAuth 2.0) and RFC 7636 (PKCE) for secure authorization code flow.

## Architecture

### Components

**1. OAuth Endpoints Module** (`alexa_oauth_endpoints.py`)
- **Size**: 19.2 KB
- **Language**: Python 3.13 (aiohttp async)
- **Purpose**: OAuth 2.0 authorization server implementation
- **Location**: `/data/alexa_oauth_endpoints.py` (Music Assistant container)

**Key Classes/Functions**:
- `authorize_endpoint(request)` - OAuth authorization endpoint (GET /alexa/authorize)
- `token_endpoint(request)` - Token exchange endpoint (POST /alexa/token)
- `handle_authorization_code_grant(body)` - Authorization code grant handler
- `handle_refresh_token_grant(body)` - Refresh token handler
- `verify_access_token(token)` - Token verification utility
- `register_oauth_routes(app)` - aiohttp route registration

**2. Client Credentials Manager**
- **Storage**: `oauth_clients.json` config file
- **Format**: JSON with client_id, client_secret, redirect_uris
- **Fallback**: Environment variable `ALEXA_OAUTH_CLIENT_SECRET`
- **Function**: `load_oauth_clients()` - Loads from file or env
- **Function**: `validate_client(client_id, client_secret)` - Validates credentials

**3. Standalone Server Script** (`start_oauth_server.py`)
- **Size**: 1.5 KB
- **Language**: Python 3.13
- **Purpose**: Standalone aiohttp server wrapper
- **Location**: `/data/start_oauth_server.py` (Music Assistant container)
- **Port**: 8096 (configurable)
- **Purpose**: Separate from Music Assistant web server (port 8095)

**4. Integration Script** (`register_oauth_routes.py`)
- **Size**: 4.1 KB
- **Language**: Python 3.13
- **Purpose**: Route registration and testing
- **Modes**: Standalone server, integration test, route validation

## Security Implementation

### OAuth 2.0 Authorization Code Grant Flow

```
1. Alexa → OAuth Server: GET /authorize (with PKCE challenge)
   - Parameters: response_type, client_id, redirect_uri, state, code_challenge
   - Security: State parameter for CSRF protection

2. OAuth Server → Alexa: 302 Redirect with authorization code
   - Code validity: 5 minutes
   - One-time use: Code deleted after exchange

3. Alexa → OAuth Server: POST /token (with PKCE verifier)
   - Parameters: code, redirect_uri, client_id, client_secret, code_verifier
   - Security: client_secret required (HTTP Basic auth)

4. OAuth Server → Alexa: Access token + refresh token (JSON)
   - access_token: Cryptographically random (32 bytes, URL-safe base64)
   - refresh_token: Cryptographically random (32 bytes, URL-safe base64)
   - expires_in: 3600 seconds (1 hour)
```

### PKCE (Proof Key for Code Exchange) Implementation

**Prevention**: Authorization code interception attacks

**Implementation**:
- Client generates random `code_verifier` (32 bytes)
- Client hashes verifier: `code_challenge = base64url(SHA256(code_verifier))`
- Client sends challenge in /authorize request
- OAuth server stores challenge with authorization code
- Client sends verifier in /token request
- OAuth server verifies: `base64url(SHA256(verifier)) == stored_challenge`

**Function**: `hash_code_verifier(verifier)` in alexa_oauth_endpoints.py

### Client Credential Validation

**Location**: `token_endpoint()` and `handle_authorization_code_grant()`

**Validation**:
1. Check client_id exists in registered clients
2. Check client_secret matches registered secret
3. Return 401 Unauthorized if either fails
4. Error message: "Client authentication failed"

**Security**: Prevents unauthorized access token issuance

### Token Storage

**In-Memory Storage** (current):
```python
tokens = {
    'user_id': {
        'access_token': '...',
        'refresh_token': '...',
        'expires_at': 1234567890,
        'scope': 'music.read music.control'
    }
}
```

**Production Enhancement**: Replace with Redis or encrypted database

**Rationale**: Current implementation sufficient for MVP/testing, need persistent store for production

## Deployment

### Container Setup

**Host**: haboxhill.local (Home Assistant)
**Container**: addon_d5369777_music_assistant (Music Assistant)
**OS**: Alpine Linux 3.20
**Python**: 3.13
**Framework**: aiohttp 4.0+

### File Locations (Inside Container)

```
/data/
  ├── alexa_oauth_endpoints.py      (Main OAuth implementation)
  ├── oauth_clients.json            (Client credentials config)
  ├── start_oauth_server.py         (Standalone server wrapper)
  ├── register_oauth_routes.py      (Route registration + testing)
  └── start_oauth_server.log        (Server output log)
```

### Port Configuration

**Internal**:
- Port 8096: OAuth server (separate from Music Assistant 8095)
- Network: Listens on 0.0.0.0:8096 (all interfaces inside container)

**Network Isolation**:
- Music Assistant container bridge network
- OAuth server accessible to Docker DNS: `music-assistant:8096`
- Exposed via Tailscale Funnel (see TAILSCALE_FUNNEL_IMPLEMENTATION_ALEXA.md)

### Environment Variables

**Required**:
- `ALEXA_OAUTH_CLIENT_SECRET`: Client secret (fallback if oauth_clients.json missing)

**Optional**:
- `MASS_CONFIG_DIR`: Config directory (default: `/config`)

## Endpoints

### GET /health
**Purpose**: Health check endpoint
**Response**:
```json
{
  "status": "ok",
  "message": "Music Assistant OAuth Server",
  "endpoints": ["/alexa/authorize", "/alexa/token", "/health"]
}
```
**Status Code**: 200 OK

### GET /alexa/authorize
**Purpose**: OAuth authorization endpoint (user login redirect)

**Query Parameters**:
```
response_type=code              (required, must be "code")
client_id=amazon-alexa          (required)
redirect_uri=https://...        (required, must match registered URI)
state=<CSRF_token>              (required, echoed back)
code_challenge=<hash>           (required for PKCE)
code_challenge_method=S256      (required, only S256 supported)
scope=music.read music.control  (optional)
```

**Response**: 302 Redirect
```
Location: https://redirect_uri?code=<auth_code>&state=<same_state>
```

**Status Code**: 302 Found (redirect)

**Error Responses**:
- 400: Missing/invalid parameters
- 400: Invalid response_type (not "code")
- 400: Invalid code_challenge_method (not "S256")

### POST /alexa/token
**Purpose**: Token exchange endpoint (authorization code → access token)

**Request**:
```
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
code=<auth_code>
redirect_uri=https://...
client_id=amazon-alexa
client_secret=<secret>
code_verifier=<plain_text>
```

**Response**: 200 OK
```json
{
  "access_token": "...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "...",
  "scope": "music.read music.control"
}
```

**Error Responses**:
- 400: Missing required parameters
- 401: Client authentication failed (invalid client_id or secret)
- 400: Invalid authorization code
- 400: Authorization code expired
- 400: PKCE verification failed (code_verifier doesn't match challenge)

## Client Configuration

### File: oauth_clients.json

**Format**:
```json
{
  "amazon-alexa": {
    "client_secret": "Nv8Xh-zG_wR3mK2pL4jF9qY6bT5vC1xD0sW7aM",
    "redirect_uris": [
      "https://pitangui.amazon.com/auth/o2/callback",
      "https://layla.amazon.com/api/skill/link/MKXZK47785HJ2",
      "https://alexa.amazon.co.jp/api/skill/link/MKXZK47785HJ2"
    ]
  }
}
```

**Security**:
- File permissions: 644 (readable, not executable)
- Location: `/data/oauth_clients.json` (inside container)
- Excluded from git/version control
- Environment variable fallback for deployment

**Management**:
- No UI for client management (future enhancement)
- Manual editing of JSON file for now
- Restart OAuth server after changes

## Testing

### Local Test Suite

**File**: `alexa_oauth_endpoints.py` includes built-in test function

**Run Locally**:
```bash
cd /Users/jason/Library/Mobile.../MusicAssistantApple
ALEXA_OAUTH_CLIENT_SECRET="Nv8Xh-zG_wR3mK2pL4jF9qY6bT5vC1xD0sW7aM" python3 alexa_oauth_endpoints.py
```

**Test Coverage**:
- ✅ PKCE pair generation
- ✅ Authorization code generation
- ✅ Code exchange for access token
- ✅ Access token verification
- ✅ Token refresh functionality
- ✅ Invalid credentials rejection
- ✅ Authorization code expiry

### Container Test

```bash
ssh root@haboxhill.local
docker exec addon_d5369777_music_assistant curl http://localhost:8096/health
```

## Integration Points

### With Music Assistant
- Same container, separate port (8095 ↔ 8096)
- No direct code integration (standalone server)
- Can restart OAuth without restarting MA

### With Alexa Skill
- OAuth endpoints: `/alexa/authorize`, `/alexa/token`
- Client credentials: Client ID + Secret configured in Alexa console
- Redirect URIs: Alexa-managed (automatically generated)

### With Tailscale Funnel
- Internal: localhost:8096 (Music Assistant container)
- External: https://haboxhill.tail1cba6.ts.net (public proxy)
- See: TAILSCALE_FUNNEL_IMPLEMENTATION_ALEXA.md

## Known Limitations & Future Enhancements

### Current Limitations
1. **In-Memory Token Storage**: Lost on restart
   - Fix: Use Redis or encrypted database

2. **No Token Encryption**: Tokens stored as plaintext in memory
   - Fix: Implement Fernet (AES-128) encryption

3. **Single Client Only**: oauth_clients.json hardcoded for amazon-alexa
   - Fix: Multi-client management UI

4. **No Audit Logging**: Authorization events not logged
   - Fix: Add audit trail for compliance

### Production Enhancements
1. Rate limiting per client_id
2. Token revocation endpoint
3. Scope-based permissions
4. User consent screen
5. Persistent token storage
6. Token rotation
7. Audit logging

## References

- **RFC 6749**: OAuth 2.0 Authorization Framework
  - https://tools.ietf.org/html/rfc6749

- **RFC 7636**: Proof Key for Code Exchange (PKCE)
  - https://tools.ietf.org/html/rfc7636

- **aiohttp Documentation**:
  - https://docs.aiohttp.org

- **Music Assistant OAuth Contract**:
  - See: docs/03_INTERFACES/ALEXA_OAUTH_ENDPOINTS_CONTRACT.md

## Version History

- **2025-10-26**: OAuth server implementation complete, tested, and deployed
- **2025-10-25**: OAuth endpoints designed and implemented
