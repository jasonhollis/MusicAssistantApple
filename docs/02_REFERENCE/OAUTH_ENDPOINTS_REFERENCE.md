# OAuth Endpoints Quick Reference
**Purpose**: Quick lookup for OAuth endpoint URLs, parameters, and responses
**Audience**: Operators, Developers, QA Engineers
**Layer**: 02_REFERENCE
**Date**: 2025-10-26

**Related**:
- [OAuth Endpoints Contract](../03_INTERFACES/ALEXA_OAUTH_ENDPOINTS_CONTRACT.md) - Full API specification
- [OAuth Server Implementation](../04_INFRASTRUCTURE/OAUTH_SERVER_IMPLEMENTATION.md) - Technical details
- [OAuth Server Startup](../05_OPERATIONS/OAUTH_SERVER_STARTUP.md) - Operational procedures

---

## Endpoints

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/health` | GET | Server health check | No |
| `/alexa/authorize` | GET | Authorization request (user consent) | User session |
| `/alexa/token` | POST | Token exchange (code → token) | Client credentials |

---

## Deployment URLs

| Environment | Base URL | Port | Access | Notes |
|-------------|----------|------|--------|-------|
| **Local Dev** | `http://localhost:8096` | 8096 | Container-internal | Testing only |
| **Tailscale Funnel** | `https://haboxhill.tail1cba6.ts.net` | 443 (proxied to 8096) | Public HTTPS | Current production |
| **Nabu Casa** | `https://music.jasonhollis.com` | 443 (proxied to 8096) | Public HTTPS | Future deployment option |

**Current Production**: Tailscale Funnel (as of 2025-10-26)

---

## Client Configuration

### Amazon Alexa Client

| Parameter | Value | Location |
|-----------|-------|----------|
| **client_id** | `amazon-alexa` | oauth_clients.json |
| **client_secret** | `Nv8Xh-zG_wR3mK2pL4jF9qY6bT5vC1xD0sW7aM` | oauth_clients.json (SENSITIVE) |
| **scopes** | `music.read music.control` | OAuth server default |

### Alexa Redirect URIs

| Region | Redirect URI | Usage |
|--------|--------------|-------|
| **US (North America)** | `https://pitangui.amazon.com/auth/o2/callback` | Primary |
| **US (Mobile)** | `https://layla.amazon.com/api/skill/link/MKXZK47785HJ2` | Alexa app |
| **Japan** | `https://alexa.amazon.co.jp/api/skill/link/MKXZK47785HJ2` | Japan region |

---

## HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| **200** | Success | Health check, token response |
| **302** | Redirect | Authorization redirect to client |
| **400** | Bad Request | Invalid parameters, expired code, PKCE failure |
| **401** | Unauthorized | Invalid client credentials |
| **500** | Server Error | Internal server error |
| **503** | Service Unavailable | OAuth server not running |

---

## Authorization Endpoint Details

### GET /alexa/authorize

**Query Parameters**:
| Parameter | Required | Example Value | Notes |
|-----------|----------|---------------|-------|
| `response_type` | Yes | `code` | Must be "code" |
| `client_id` | Yes | `amazon-alexa` | Registered client ID |
| `redirect_uri` | Yes | `https://pitangui.amazon.com/auth/o2/callback` | Must match registered URI |
| `state` | Yes | `random-csrf-token-123` | CSRF protection, echoed back |
| `code_challenge` | Yes | `base64url(sha256(verifier))` | PKCE challenge |
| `code_challenge_method` | Yes | `S256` | Only S256 supported |
| `scope` | Optional | `music.read music.control` | Space-separated scopes |

**Success Response** (HTTP 302):
```
Location: https://redirect_uri?code=AUTH_CODE&state=SAME_STATE
```

**Error Responses**:
- `400 Bad Request`: Missing required parameters
- `400 Bad Request`: Invalid response_type (not "code")
- `400 Bad Request`: Invalid code_challenge_method (not "S256")
- `401 Unauthorized`: Invalid client_id

---

## Token Endpoint Details

### POST /alexa/token

**Request Headers**:
```
Content-Type: application/x-www-form-urlencoded
```

**Request Body (Authorization Code Grant)**:
| Parameter | Required | Example Value | Notes |
|-----------|----------|---------------|-------|
| `grant_type` | Yes | `authorization_code` | Grant type |
| `code` | Yes | `auth-code-from-authorize` | From /authorize redirect |
| `redirect_uri` | Yes | `https://pitangui.amazon.com/auth/o2/callback` | Must match original |
| `client_id` | Yes | `amazon-alexa` | Client identifier |
| `client_secret` | Yes | `Nv8Xh-zG_wR3mK2pL4jF9qY6bT5vC1xD0sW7aM` | Client secret |
| `code_verifier` | Yes | `random-string-43-128-chars` | PKCE verifier (plain text) |

**Request Body (Refresh Token Grant)**:
| Parameter | Required | Example Value | Notes |
|-----------|----------|---------------|-------|
| `grant_type` | Yes | `refresh_token` | Grant type |
| `refresh_token` | Yes | `refresh-token-from-previous-response` | From earlier token response |
| `client_id` | Yes | `amazon-alexa` | Client identifier |
| `client_secret` | Yes | `Nv8Xh-zG_wR3mK2pL4jF9qY6bT5vC1xD0sW7aM` | Client secret |

**Success Response** (HTTP 200):
```json
{
  "access_token": "random-64-char-token",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "random-64-char-refresh-token",
  "scope": "music.read music.control"
}
```

**Error Responses**:
- `400 Bad Request`: Missing required parameters
- `401 Unauthorized`: Invalid client_id or client_secret
- `400 Bad Request`: Invalid or expired authorization code
- `400 Bad Request`: Authorization code already used
- `400 Bad Request`: PKCE verification failed
- `400 Bad Request`: Invalid refresh token

---

## Token Lifetimes

| Token Type | Lifetime | Renewable | Notes |
|------------|----------|-----------|-------|
| **Authorization Code** | 5 minutes | No | Single-use, then deleted |
| **Access Token** | 1 hour | Yes (via refresh token) | Used for API requests |
| **Refresh Token** | Long-lived | Yes (new one issued on refresh) | Used to get new access tokens |

---

## Example Commands

### Health Check

**Request**:
```bash
curl http://localhost:8096/health
```

**Expected Response**:
```json
{
  "status": "ok",
  "server": "oauth",
  "port": 8096
}
```

---

### Authorization Request (Simulated)

**Note**: This is typically done via browser redirect from Alexa, not curl.

**Request**:
```bash
curl -v "http://localhost:8096/alexa/authorize?\
client_id=amazon-alexa&\
redirect_uri=https://pitangui.amazon.com/auth/o2/callback&\
state=random123&\
response_type=code&\
code_challenge=abc123xyz&\
code_challenge_method=S256"
```

**Expected Response**:
```
HTTP/1.1 302 Found
Location: https://pitangui.amazon.com/auth/o2/callback?code=AUTH_CODE&state=random123
```

---

### Token Exchange (Authorization Code)

**Request**:
```bash
curl -X POST http://localhost:8096/alexa/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code" \
  -d "code=AUTH_CODE_FROM_AUTHORIZE" \
  -d "redirect_uri=https://pitangui.amazon.com/auth/o2/callback" \
  -d "client_id=amazon-alexa" \
  -d "client_secret=Nv8Xh-zG_wR3mK2pL4jF9qY6bT5vC1xD0sW7aM" \
  -d "code_verifier=ORIGINAL_VERIFIER_PLAIN_TEXT"
```

**Expected Response**:
```json
{
  "access_token": "eyJhbG...(random 64-char string)",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "eyJhbG...(random 64-char string)",
  "scope": "music.read music.control"
}
```

---

### Token Refresh

**Request**:
```bash
curl -X POST http://localhost:8096/alexa/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=REFRESH_TOKEN_FROM_PREVIOUS_RESPONSE" \
  -d "client_id=amazon-alexa" \
  -d "client_secret=Nv8Xh-zG_wR3mK2pL4jF9qY6bT5vC1xD0sW7aM"
```

**Expected Response**:
```json
{
  "access_token": "eyJhbG...(NEW random 64-char string)",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Note**: Refresh token may or may not be rotated (implementation dependent).

---

## Common Issues Quick Reference

| Symptom | Likely Cause | Quick Fix | Details |
|---------|--------------|-----------|---------|
| **Connection refused** | OAuth server not running | Restart OAuth server | See [OAuth Server Startup](../05_OPERATIONS/OAUTH_SERVER_STARTUP.md) |
| **"Invalid client"** (401) | Wrong client_secret | Check oauth_clients.json | Verify client_secret matches |
| **"PKCE verification failed"** (400) | code_verifier mismatch | Verify Alexa sends correct verifier | SHA256(verifier) must equal original challenge |
| **"Authorization code expired"** (400) | >5 min delay | Reduce time between authorize and token | Complete flow within 5 minutes |
| **"Authorization code already used"** (400) | Code reused | Generate new authorization code | Each code is single-use |
| **"Invalid refresh token"** (400) | Token not found or expired | Re-authorize to get new tokens | User must re-link account |
| **502 Bad Gateway** | Tailscale Funnel not configured | Check Tailscale Funnel status | See [Tailscale Funnel Implementation](../05_OPERATIONS/TAILSCALE_FUNNEL_IMPLEMENTATION_ALEXA.md) |

---

## PKCE Flow Quick Reference

**What is PKCE?**: Proof Key for Code Exchange - prevents authorization code interception attacks

**Client (Alexa) Side**:
1. Generate `code_verifier`: Random 43-128 character string
   ```
   code_verifier = base64url(random_bytes(32))
   ```

2. Create `code_challenge`: SHA-256 hash of verifier
   ```
   code_challenge = base64url(sha256(code_verifier))
   ```

3. Send challenge in `/authorize` request
   ```
   GET /authorize?...&code_challenge=abc123&code_challenge_method=S256
   ```

4. Send verifier in `/token` request
   ```
   POST /token
   code_verifier=original_plain_text_verifier
   ```

**Server (OAuth) Side**:
1. Store `code_challenge` with authorization code
2. When `/token` called, hash the received `code_verifier`
3. Compare: `base64url(sha256(verifier))` == stored `code_challenge`
4. If match: issue token
5. If mismatch: return 400 error

---

## Security Notes

### Secrets Management

**NEVER commit to git**:
- `oauth_clients.json` (contains client_secret)
- Any log files with tokens
- Environment files with secrets

**Storage Locations**:
- **Production**: `/data/oauth_clients.json` (inside container)
- **Fallback**: `ALEXA_OAUTH_CLIENT_SECRET` environment variable
- **Backup**: Encrypted backup of oauth_clients.json

### Token Security

**Access tokens**:
- Treat as credentials (bearer tokens)
- Valid for API requests
- Expires in 1 hour
- Should be transmitted over HTTPS only

**Refresh tokens**:
- More sensitive than access tokens (longer lifetime)
- Should be encrypted at rest
- Current implementation: In-memory (lost on restart)
- Production: Should use Redis or encrypted database

**Client secrets**:
- Must be kept confidential
- Rotate if compromised
- Current value: See oauth_clients.json (production only)

---

## Monitoring Points

**Health Check**:
- URL: `/health`
- Expected: 200 OK response
- Check frequency: Every 5 minutes
- Alert if: 3 consecutive failures

**OAuth Flow Success Rate**:
- Metric: Successful token exchanges / Total token requests
- Expected: >95%
- Alert if: <90%

**Token Expiry**:
- Authorization codes: 5-minute lifetime
- Access tokens: 1-hour lifetime
- Monitor: Expired token usage attempts (should be 0)

**Error Rates**:
- 400 Bad Request: <5% (some errors expected from invalid attempts)
- 401 Unauthorized: <1% (should be rare in production)
- 500 Server Error: 0% (alert immediately)

---

## Related Documentation

**Architecture**:
- [ADR 002: Alexa Integration Strategy](../00_ARCHITECTURE/ADR_002_ALEXA_INTEGRATION_STRATEGY.md)
- [OAuth Flow Architecture Decision](../../DECISIONS.md#decision-006)

**Interfaces**:
- [OAuth Endpoints Contract](../03_INTERFACES/ALEXA_OAUTH_ENDPOINTS_CONTRACT.md) - Full API specification

**Infrastructure**:
- [OAuth Server Implementation](../04_INFRASTRUCTURE/OAUTH_SERVER_IMPLEMENTATION.md) - Technical details
- [Tailscale Funnel OAuth Proxy](../04_INFRASTRUCTURE/TAILSCALE_FUNNEL_OAUTH_PROXY.md) - Proxy configuration

**Operations**:
- [OAuth Server Startup](../05_OPERATIONS/OAUTH_SERVER_STARTUP.md) - How to start/stop server
- [OAuth Server Troubleshooting](../05_OPERATIONS/OAUTH_AUTH_TROUBLESHOOTING.md) - Troubleshooting guide
- [Tailscale Funnel Implementation](../05_OPERATIONS/TAILSCALE_FUNNEL_IMPLEMENTATION_ALEXA.md) - Public exposure setup

**Decisions**:
- [Decision 004: OAuth Server Deployment Pattern](../../DECISIONS.md#decision-004)
- [Decision 005: Client Secret Management](../../DECISIONS.md#decision-005)
- [Decision 006: OAuth Flow Architecture](../../DECISIONS.md#decision-006)

---

**Document Version**: 1.0
**Last Updated**: 2025-10-26
**Review Date**: Monthly (or after OAuth changes)
**Maintained By**: Operations Team

---

**END OF QUICK REFERENCE**
