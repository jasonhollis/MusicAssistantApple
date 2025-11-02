# Music Assistant Alexa Public Interface Contract
**Purpose**: Define the stable interface contract that Amazon Alexa requires from Music Assistant for account linking
**Audience**: Integration developers, system architects, security auditors
**Layer**: 03_INTERFACES (stable contracts and boundaries)
**Related**:
- [Alexa Integration Constraints](../00_ARCHITECTURE/ALEXA_INTEGRATION_CONSTRAINTS.md)
- [OAuth 2.0 Reference](../02_REFERENCE/OAUTH2_FLOW.md)

---

## Intent

This document defines the **stable contract** between Amazon Alexa and Music Assistant for OAuth 2.0 account linking. This interface must remain stable regardless of how it's implemented (Layer 04) or operated (Layer 05).

## Interface Overview

**Protocol**: OAuth 2.0 Authorization Code Flow
**Transport**: HTTPS (TLS 1.2 or higher)
**Authentication**: Client credentials + authorization code
**Endpoints Required**: 3 public HTTPS endpoints

## Required Public Endpoints

### 1. Authorization Endpoint

**Purpose**: User consent and authorization code generation

**Interface Specification**:
```
Endpoint: /authorize
Method: GET
Protocol: HTTPS
Access: Public (user web browser)
```

**Required Request Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `response_type` | string | Yes | Must be "code" |
| `client_id` | string | Yes | Alexa skill client identifier |
| `redirect_uri` | string | Yes | Alexa callback URL |
| `state` | string | Yes | CSRF protection token |
| `scope` | string | No | Requested permissions (optional) |

**Required Response Behavior**:

**Success Case** (user authorizes):
```
HTTP 302 Redirect
Location: {redirect_uri}?code={authorization_code}&state={state}
```

**Denial Case** (user denies):
```
HTTP 302 Redirect
Location: {redirect_uri}?error=access_denied&state={state}
```

**Error Cases**:
```
HTTP 302 Redirect
Location: {redirect_uri}?error={error_code}&error_description={description}&state={state}
```

**Error Codes**:
- `invalid_request` - Missing or invalid parameter
- `unauthorized_client` - Client not authorized
- `unsupported_response_type` - response_type not "code"
- `invalid_scope` - Requested scope invalid
- `server_error` - Internal server error
- `temporarily_unavailable` - Service temporarily down

**Security Requirements**:
- Must validate `redirect_uri` against registered Alexa callback URLs
- Must validate `client_id` against registered Alexa skill credentials
- Must preserve `state` parameter exactly (no modification)
- Must use HTTPS with valid public certificate
- Should implement rate limiting on failed attempts

### 2. Token Endpoint

**Purpose**: Exchange authorization code for access token

**Interface Specification**:
```
Endpoint: /token
Method: POST
Protocol: HTTPS
Access: Public (Alexa service server-to-server)
Content-Type: application/x-www-form-urlencoded
```

**Required Request Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `grant_type` | string | Yes | Must be "authorization_code" |
| `code` | string | Yes | Authorization code from /authorize |
| `redirect_uri` | string | Yes | Must match /authorize redirect_uri |
| `client_id` | string | Yes | Alexa skill client identifier |
| `client_secret` | string | Yes | Alexa skill client secret |

**Required Response** (Success):
```json
HTTP 200 OK
Content-Type: application/json

{
  "access_token": "string",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "string" (optional)
}
```

**Required Response** (Error):
```json
HTTP 400 Bad Request
Content-Type: application/json

{
  "error": "error_code",
  "error_description": "human-readable description"
}
```

**Error Codes**:
- `invalid_request` - Missing or invalid parameter
- `invalid_client` - Client authentication failed
- `invalid_grant` - Invalid/expired/revoked authorization code
- `unauthorized_client` - Client not authorized for grant type
- `unsupported_grant_type` - grant_type not "authorization_code"

**Security Requirements**:
- Must authenticate client using `client_id` and `client_secret`
- Must validate authorization code is valid and not expired
- Must validate authorization code was issued to this client
- Must validate `redirect_uri` matches original request
- Authorization codes must be single-use (invalidate after exchange)
- Authorization codes should expire (recommended: 10 minutes)
- Must use HTTPS with valid public certificate
- Should implement rate limiting

### 3. Callback Endpoint (Optional but Recommended)

**Purpose**: Handle redirects from Alexa after authorization

**Interface Specification**:
```
Endpoint: /callback
Method: GET
Protocol: HTTPS
Access: Public (user web browser via Alexa redirect)
```

**Expected Request Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `code` | string | Conditional | Authorization code (if success) |
| `state` | string | Yes | State from original request |
| `error` | string | Conditional | Error code (if failure) |

**Required Response Behavior**:
- Display user-friendly success/error message
- Optionally redirect to success page
- Should not expose sensitive information in UI

**Note**: This endpoint is technically part of Alexa's flow, but Music Assistant may host it for better UX.

## TLS Requirements

**Minimum TLS Version**: TLS 1.2
**Recommended TLS Version**: TLS 1.3

**Certificate Requirements**:
- **Issuer**: Must be from publicly trusted Certificate Authority (CA)
- **Subject/SAN**: Must match the hostname used in OAuth URLs
- **Validity**: Must not be expired
- **Chain**: Must include intermediate certificates
- **Revocation**: Must not be revoked (CRL/OCSP check)

**Rejected Certificates**:
- Self-signed certificates ❌
- Internal/private CA certificates ❌
- Expired certificates ❌
- Hostname mismatch ❌
- Untrusted root CA ❌

## DNS Requirements

**Hostname Resolution**:
- Public DNS record must resolve to publicly accessible IP
- DNS record must be stable (Alexa may cache)
- Recommended: Use CNAME to managed service for flexibility

**Dynamic DNS Considerations**:
- If using dynamic IP, DNS updates must be reliable
- TTL should be short (300-600 seconds) for failover
- DNS propagation delays may affect OAuth flow

## Network Requirements

**Accessibility**:
- All three endpoints must be reachable from public internet
- No VPN/authentication required for endpoint access
- No geographic restrictions (Alexa operates globally)

**Ports**:
- Standard HTTPS port 443 (recommended)
- Custom ports allowed but complicate setup
- Port must be consistent across all OAuth URLs

**Firewall**:
- Inbound HTTPS traffic must be permitted
- Source IPs: Variable (Amazon's service IPs + user browsers)
- Cannot whitelist specific IPs (Amazon's ranges change)

## Data Contract Stability

**Stable Elements** (will not change):
- OAuth 2.0 protocol flow
- Required endpoint paths (unless both sides coordinate)
- Required parameters and their meanings
- Error codes and their semantics
- TLS certificate validation rules

**Variable Elements** (may change):
- Hostname (with DNS update)
- IP address (with routing update)
- TLS certificate (with renewal, same hostname)
- Client credentials (with re-registration)

**Versioning Strategy**:
- This interface follows OAuth 2.0 RFC 6749 (stable spec)
- No custom versioning required
- Breaking changes require new Alexa skill registration

## Security Boundaries

**Public Trust Boundary**:
- These endpoints cross the public internet boundary
- Assume hostile actors have network access
- Defense must be in the implementation (Layer 04)

**Authentication Boundaries**:
- User authentication: Handled by Music Assistant login
- Client authentication: `client_id` + `client_secret`
- Token authentication: Bearer token in subsequent API calls

**Authorization Boundaries**:
- User authorizes Alexa skill to access Music Assistant
- Scope of access defined by OAuth scopes (if used)
- Revocation should be possible (token invalidation)

## Failure Modes

**Client-Detectable Failures**:
- Certificate validation failure → User sees browser warning
- DNS resolution failure → Connection timeout
- Network unreachable → Connection timeout
- Server error → HTTP 500 response

**Server-Detectable Failures**:
- Invalid client credentials → `invalid_client` error
- Expired authorization code → `invalid_grant` error
- Invalid redirect URI → `invalid_request` error

**Silent Failures** (require monitoring):
- Firewall blocks traffic → Connection timeout (indistinguishable from network failure)
- Certificate expired → TLS handshake failure
- DNS points to wrong IP → Wrong service responds

## Monitoring Requirements

**Health Checks**:
- Endpoint availability (HTTP 200 response)
- TLS certificate validity (expiration date)
- DNS resolution correctness
- Authorization flow success rate
- Token exchange success rate

**Metrics to Track**:
- OAuth flow completion rate
- Authorization code usage (single-use validation)
- Token issuance rate
- Error rates by error type
- TLS handshake failures

## Compatibility Requirements

**Amazon Alexa Service**:
- OAuth client implementation by Amazon
- Cannot modify Alexa's behavior
- Must conform to Alexa's expectations

**Web Browsers** (for user consent):
- Modern browsers (Chrome, Firefox, Safari, Edge)
- Mobile browsers (iOS Safari, Android Chrome)
- Must handle OAuth redirects correctly

**Music Assistant Service**:
- Must implement OAuth provider endpoints
- Must integrate with Music Assistant authentication
- Must issue valid access tokens for Alexa to use

## Testing Contract Compliance

**Manual Tests**:
1. Access `/authorize` with valid parameters → Should show login/consent UI
2. Authorize access → Should redirect to `redirect_uri` with code
3. POST to `/token` with valid code → Should return access token
4. POST to `/token` with same code again → Should return error (single-use)
5. POST to `/token` with expired code → Should return error

**Automated Tests**:
- TLS certificate validation (check expiration, CA trust, hostname)
- DNS resolution (correct IP, reasonable TTL)
- OAuth parameter validation (missing/invalid parameters return errors)
- State parameter preservation (exact match required)
- Authorization code single-use enforcement

**Security Tests**:
- CSRF protection (state parameter validation)
- Client authentication (invalid credentials rejected)
- Redirect URI validation (unregistered URIs rejected)
- Authorization code expiration
- Rate limiting on failed attempts

## See Also

- **[Alexa Integration Constraints](../00_ARCHITECTURE/ALEXA_INTEGRATION_CONSTRAINTS.md)** - Why this interface is required
- **[OAuth 2.0 Reference](../02_REFERENCE/OAUTH2_FLOW.md)** - Protocol details
- **[Public Exposure Options](../04_INFRASTRUCTURE/ALEXA_PUBLIC_EXPOSURE_OPTIONS.md)** - How to implement this interface
- **[Viable Implementation Paths](../05_OPERATIONS/MUSIC_ASSISTANT_ALEXA_VIABLE_PATHS.md)** - Step-by-step procedures
