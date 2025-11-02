# OAuth 2.0 Constants and Reference Data
**Purpose**: Quick reference for OAuth token formats, lifetimes, and constants
**Audience**: Developers, operators, security auditors
**Layer**: 02_REFERENCE
**Related**: [00_ARCHITECTURE/OAUTH_PRINCIPLES.md](../00_ARCHITECTURE/OAUTH_PRINCIPLES.md)

## Intent

This document provides quick-lookup reference data for OAuth implementation, including token lifetimes, format specifications, error codes, and cryptographic parameters. All values are technology-agnostic and based on RFC specifications.

## Token Lifetimes

### Authorization Code
```
Lifetime:        5 minutes (300 seconds)
Usage:           Single-use only
Storage:         Server-side only
Transport:       URL query parameter (via redirect)
Validation:      Timestamp check + single-use check
```

**Rationale**: Short lifetime limits window for interception attacks. Authorization codes are ephemeral - just long enough for client to exchange them.

### Access Token
```
Lifetime:        1 hour (3600 seconds)
Usage:           Multiple uses until expiration
Storage:         Client-side (secure storage)
Transport:       HTTP Authorization header (Bearer scheme)
Validation:      Timestamp check + signature verification
```

**Rationale**: Short lifetime limits damage from token theft while long enough to avoid excessive refresh requests.

### Refresh Token
```
Lifetime:        90 days (7,776,000 seconds)
Usage:           Multiple uses until expiration
Storage:         Client-side (secure storage, encrypted)
Transport:       HTTP POST body (token endpoint only)
Validation:      Timestamp check + signature verification + revocation check
```

**Rationale**: Long lifetime enables seamless token renewal without user re-authorization. 90 days balances security with usability.

## Token Format Specifications

### Authorization Code Format
```
Encoding:        URL-safe base64
Length:          43 characters (32 bytes of entropy)
Character set:   A-Z, a-z, 0-9, -, _
Example:         5BXfFUdOyRvcJ5OOza2MRdKiN3fq3tIfLfge_7_h2AQ
Generation:      cryptographically secure random (secrets.token_urlsafe)
```

### Access Token Format
```
Encoding:        URL-safe base64
Length:          43 characters (32 bytes of entropy)
Character set:   A-Z, a-z, 0-9, -, _
Example:         fDpnBe_wSfmkJebHQkfMfKzfN_AeFXMcYQxow40eusE
Generation:      cryptographically secure random (secrets.token_urlsafe)
Type:            Bearer token (RFC 6750)
```

### Refresh Token Format
```
Encoding:        URL-safe base64
Length:          43 characters (32 bytes of entropy)
Character set:   A-Z, a-z, 0-9, -, _
Example:         hHBMuKyImOepseExdJrYeaTLfIZlhdOiYNSJdq2q1LM
Generation:      cryptographically secure random (secrets.token_urlsafe)
Type:            Opaque token (no structure)
```

### State Parameter Format
```
Encoding:        URL-safe base64
Min Length:      22 characters (16 bytes of entropy)
Character set:   A-Z, a-z, 0-9, -, _
Example:         8H3kP9mN2vQ7xW1fZ5jL4r
Generation:      cryptographically secure random
Purpose:         CSRF protection
```

## PKCE Parameters

### Code Verifier
```
Encoding:        URL-safe characters
Length:          43-128 characters (recommended: 64)
Character set:   A-Z, a-z, 0-9, -, _, ., ~
Entropy:         256+ bits
Example:         dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk
Generation:      cryptographically secure random
```

### Code Challenge
```
Algorithm:       SHA-256
Encoding:        URL-safe base64 (without padding)
Length:          43 characters
Example:         E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
Computation:     base64url(SHA256(code_verifier))
Method:          S256 (REQUIRED - plain not supported)
```

**PKCE Validation Formula**:
```
server_challenge = base64url(SHA256(client_code_verifier))
validation_result = (server_challenge == stored_code_challenge)
```

## Scope Definitions

### Available Scopes

| Scope | Description | Permissions Granted |
|-------|-------------|---------------------|
| `music.read` | Read-only access to music library | List playlists, artists, albums, tracks |
| `music.control` | Control playback | Play, pause, skip, volume, queue management |
| `user:read` | Read user profile | Username, preferences, settings |

### Scope Syntax
```
Format:          Space-separated list
Example:         "music.read music.control user:read"
URL Encoding:    "music.read+music.control+user%3Aread"
Validation:      Each scope checked against allowed list
```

### Default Scope
```
Default:         "music.read music.control"
Applied When:    Client does not request specific scopes
Rationale:       Minimum permissions for basic music control
```

## Error Codes

### Authorization Endpoint Errors

| Error Code | Description | User-Facing Message |
|------------|-------------|---------------------|
| `invalid_request` | Missing required parameter | "Invalid request. Please try again." |
| `unauthorized_client` | Client not registered | "This application is not authorized." |
| `access_denied` | User denied authorization | "You cancelled account linking." |
| `unsupported_response_type` | response_type != code | "This authorization method is not supported." |
| `invalid_scope` | Requested scope not allowed | "Requested permissions are not available." |
| `server_error` | Internal server error | "Something went wrong. Please try again." |
| `temporarily_unavailable` | Server overloaded | "Service temporarily unavailable." |

### Token Endpoint Errors

| Error Code | HTTP Status | Description | Retry? |
|------------|-------------|-------------|--------|
| `invalid_request` | 400 | Missing parameter | No - fix request |
| `invalid_client` | 401 | Client authentication failed | No - check credentials |
| `invalid_grant` | 400 | Code invalid/expired/used | No - get new code |
| `unauthorized_client` | 400 | Client not allowed this grant | No - configuration issue |
| `unsupported_grant_type` | 400 | grant_type not supported | No - use correct grant_type |
| `invalid_scope` | 400 | Requested scope not allowed | No - request valid scopes |

### Error Response Format
```json
{
  "error": "invalid_grant",
  "error_description": "Authorization code has expired"
}
```

## Client Configuration

### Registered Clients

#### Client: amazon-alexa
```
Client ID:         amazon-alexa
Client Type:       public
Authentication:    PKCE (no client_secret)
Allowed Scopes:    music.read, music.control, user:read
Redirect URIs:
  - https://pitangui.amazon.com/auth/o2/callback
  - https://layla.amazon.com/api/skill/link/MKXZK47785HJ2
  - https://alexa.amazon.co.jp/api/skill/link/MKXZK47785HJ2
Grant Types:       authorization_code, refresh_token
```

### Client Type Characteristics

| Attribute | Confidential Client | Public Client |
|-----------|---------------------|---------------|
| Example | Backend web service | Mobile app, voice assistant |
| Secret Storage | Yes (secure server) | No (extractable by user) |
| Authentication | client_id + client_secret | PKCE (code_challenge) |
| Security Model | Shared secret | Cryptographic proof |
| RFC Reference | RFC 6749 Section 2.1 | RFC 6749 Section 2.1 + RFC 7636 |

## Cryptographic Parameters

### Minimum Entropy Requirements

| Parameter | Minimum Entropy | Recommended Length |
|-----------|-----------------|-------------------|
| Authorization Code | 256 bits | 32 bytes → 43 chars (base64url) |
| Access Token | 256 bits | 32 bytes → 43 chars (base64url) |
| Refresh Token | 256 bits | 32 bytes → 43 chars (base64url) |
| State Parameter | 128 bits | 16 bytes → 22 chars (base64url) |
| Code Verifier (PKCE) | 256 bits | 32-96 bytes → 43-128 chars |

### Hash Algorithm Specifications

| Use Case | Algorithm | Output Length |
|----------|-----------|---------------|
| PKCE code_challenge | SHA-256 | 256 bits (32 bytes) |
| Token signatures | HMAC-SHA256 | 256 bits (32 bytes) |
| Password hashing | bcrypt or Argon2 | N/A (for user auth, not OAuth) |

## HTTP Headers

### Authorization Request Headers
```
GET /alexa/authorize?... HTTP/1.1
Host: oauth.example.com
User-Agent: Amazon-Alexa/iOS-18.7
Accept: text/html
Accept-Language: en-US
```

### Token Request Headers
```
POST /alexa/token HTTP/1.1
Host: oauth.example.com
Content-Type: application/x-www-form-urlencoded
User-Agent: Amazon-Alexa-Service/1.0
Content-Length: 254
```

### Resource API Request Headers (using access token)
```
GET /api/playlists HTTP/1.1
Host: api.example.com
Authorization: Bearer fDpnBe_wSfmkJebHQkfMfKzfN_AeFXMcYQxow40eusE
Accept: application/json
```

## URL Parameter Encoding

### Authorization Request Parameters
```
Base URL:        https://oauth.example.com/alexa/authorize
Parameters:
  response_type: code
  client_id:     amazon-alexa
  redirect_uri:  https://pitangui.amazon.com/auth/o2/callback (URL-encoded)
  state:         8H3kP9mN2vQ7xW1fZ5jL4r
  scope:         music.read+music.control (space encoded as +)
  code_challenge: E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM
  code_challenge_method: S256

Full URL:
https://oauth.example.com/alexa/authorize?response_type=code&client_id=amazon-alexa&redirect_uri=https%3A%2F%2Fpitangui.amazon.com%2Fauth%2Fo2%2Fcallback&state=8H3kP9mN2vQ7xW1fZ5jL4r&scope=music.read+music.control&code_challenge=E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM&code_challenge_method=S256
```

### Token Request POST Body
```
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=5BXfFUdOyRvcJ5OOza2MRdKiN3fq3tIfLfge_7_h2AQ&
redirect_uri=https%3A%2F%2Fpitangui.amazon.com%2Fauth%2Fo2%2Fcallback&
client_id=amazon-alexa&
code_verifier=dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk
```

## Token Response Format

### Successful Token Response
```json
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

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `access_token` | string | Yes | Bearer token for API access |
| `token_type` | string | Yes | Always "Bearer" per RFC 6750 |
| `expires_in` | integer | Yes | Seconds until token expiration (3600) |
| `refresh_token` | string | Yes* | Token for obtaining new access token |
| `scope` | string | No** | Granted scopes (if different from request) |

*Required for authorization_code grant, optional for refresh_token grant
**Required if granted scopes differ from requested scopes

## Timeline: Authorization Code Lifecycle

```
Time 0:00      User approves authorization
               ↓
               Authorization code generated
               Expires at: Time 5:00 (5 minutes)

Time 0:05      Alexa exchanges code for tokens
               ↓
               Authorization code invalidated (single-use)
               Access token generated
               Expires at: Time 1:05:05 (1 hour)
               Refresh token generated
               Expires at: Time 2160:05:05 (90 days)

Time 1:05:05   Access token expires
               ↓
               Alexa uses refresh token
               New access token generated
               Expires at: Time 2:05:10
               Refresh token remains valid

Time 2160:05:05  Refresh token expires
                 ↓
                 User must re-authorize
                 New authorization code → New tokens
```

## Validation Checklists

### Authorization Code Validation
- [ ] Code exists in server storage
- [ ] Code not expired (created <5 minutes ago)
- [ ] Code not previously used (single-use check)
- [ ] client_id matches code's client_id
- [ ] redirect_uri matches code's redirect_uri
- [ ] code_verifier validates against code_challenge (PKCE)

### Access Token Validation
- [ ] Token exists in server storage
- [ ] Token not expired (created <1 hour ago)
- [ ] Token not revoked (check revocation list)
- [ ] Requested scope covered by token's scope
- [ ] Token signature valid (if using signed tokens)

### Refresh Token Validation
- [ ] Token exists in server storage
- [ ] Token not expired (created <90 days ago)
- [ ] Token not revoked (check revocation list)
- [ ] client_id matches token's client_id
- [ ] Token signature valid (if using signed tokens)

## Real-World Example: Captured Alexa Request

### Authorization Request (Oct 26, 2025 20:11:26 UTC)
```
GET /alexa/authorize?
  client_id=amazon-alexa&
  response_type=code&
  redirect_uri=https%3A%2F%2Falexa.amazon.co.jp%2Fapi%2Fskill%2Flink%2FMKXZK47785HJ2&
  state=AbCdEfGh123456&
  scope=music.control+user%3Aread

User-Agent: Amazon-Alexa/iOS-18.7
Source IP: User's iPhone (Australia)
```

### Token Exchange Request (Oct 26, 2025 20:11:29 UTC)
```
POST /alexa/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code&
code=5BXfFUdOyRvcJ5OOza2MRdKiN3fq3tIfLfge_7_h2AQ&
client_id=amazon-alexa&
redirect_uri=https%3A%2F%2Falexa.amazon.co.jp%2Fapi%2Fskill%2Flink%2FMKXZK47785HJ2

User-Agent: Amazon-Alexa-Service/1.0
Source IP: 54.240.230.242 (Amazon AWS - Tokyo region)
```

**Time Delta**: 3 seconds between authorization approval and token exchange
**Observation**: Amazon servers exchange code very quickly after user approval

## See Also

- **[00_ARCHITECTURE/OAUTH_PRINCIPLES.md](../00_ARCHITECTURE/OAUTH_PRINCIPLES.md)** - OAuth architectural principles
- **[01_USE_CASES/ALEXA_ACCOUNT_LINKING.md](../01_USE_CASES/ALEXA_ACCOUNT_LINKING.md)** - User workflows
- **[03_INTERFACES/OAUTH_ENDPOINTS.md](../03_INTERFACES/OAUTH_ENDPOINTS.md)** - API specifications
