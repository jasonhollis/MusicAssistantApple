# Tailscale OAuth Routing Contract
**Purpose**: Define the stable routing contract for exposing Music Assistant OAuth endpoints via Tailscale Funnel
**Audience**: Network engineers, DevOps, system integrators
**Layer**: 03_INTERFACES
**Related**: [ALEXA_OAUTH_ENDPOINTS_CONTRACT](ALEXA_OAUTH_ENDPOINTS_CONTRACT.md), [HABOXHILL_NETWORK_TOPOLOGY](../04_INFRASTRUCTURE/HABOXHILL_NETWORK_TOPOLOGY.md)

## Intent

This document defines the **routing contract** between Tailscale Funnel (public internet endpoint) and Music Assistant OAuth server (internal container). This contract must remain stable even as the underlying infrastructure changes, ensuring that Alexa services can reliably reach OAuth endpoints.

**Key Principle**: The public URL structure and routing behavior are **interface contracts** that external systems (Alexa) depend on. Implementation details (container IPs, port numbers, proxy configuration) can change freely as long as the contract is maintained.

## Routing Contract Overview

### Public Interface (Stable Contract)

**Public Base URL**: `https://a0d7b954-tailscale.ts.net`

**Contracted Endpoints**:
| Public URL | Target Service | Contract |
|------------|----------------|----------|
| `https://a0d7b954-tailscale.ts.net/health` | OAuth Health Check | MUST return 200 OK with JSON status |
| `https://a0d7b954-tailscale.ts.net/alexa/authorize` | OAuth Authorization | MUST handle OAuth 2.0 authorization requests |
| `https://a0d7b954-tailscale.ts.net/alexa/token` | OAuth Token Exchange | MUST handle OAuth 2.0 token requests |

**Protocol Requirements**:
- **TLS**: MUST use HTTPS (port 443)
- **TLS Version**: TLSv1.2 or higher
- **Certificate**: Managed by Tailscale (automatic renewal)
- **HTTP Version**: HTTP/1.1 minimum, HTTP/2 preferred

**Response Time SLA**:
- Health endpoint: < 500ms
- Authorization endpoint: < 2 seconds
- Token endpoint: < 1 second

### Internal Interface (Implementation Detail)

**Internal Base URL**: `http://music-assistant:8096` (Docker DNS)
**Alternative**: `http://localhost:8096` (from host)
**Alternative**: `http://172.17.0.X:8096` (container IP - subject to change)

**Note**: Internal URLs are **NOT part of the contract** and may change due to:
- Container IP reassignment
- Port reconfiguration
- Network topology changes
- Container orchestration changes

## Network Path Contract

### Guaranteed Path

```
┌─────────────────────────────────────────────────────────────────┐
│ External Client (Alexa)                                         │
│ - Any IP address                                                │
│ - Amazon IP ranges                                              │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ HTTPS (port 443)
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Tailscale Funnel (Public Endpoint)                             │
│ - URL: https://a0d7b954-tailscale.ts.net                       │
│ - TLS Termination: Handled by Tailscale infrastructure         │
│ - Certificate: Auto-managed by Tailscale                       │
│ - Availability: 99.9% SLA (Tailscale service)                  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ TLS-terminated, HTTP forwarding
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Tailscale Container (Reverse Proxy Layer)                      │
│ - Container: addon_a0d7b954_tailscale                          │
│ - Network: Host mode (access to all host interfaces)           │
│ - Responsibility: Route requests to Music Assistant            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP (internal, no encryption needed)
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Docker Bridge Network                                           │
│ - Internal network between containers                           │
│ - Provides DNS resolution (music-assistant)                     │
│ - Isolated from external access                                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP to port 8096
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ Music Assistant Container (OAuth Server)                       │
│ - Container: music-assistant                                    │
│ - Service: OAuth Server (port 8096)                            │
│ - Endpoints: /health, /alexa/authorize, /alexa/token          │
└─────────────────────────────────────────────────────────────────┘
```

### Contract Guarantees

**Guarantee 1: Public URL Stability**
- Public base URL (`https://a0d7b954-tailscale.ts.net`) MUST NOT change
- If Tailscale hostname changes, redirect MUST be provided for 90 days
- Endpoint paths (`/health`, `/alexa/*`) MUST remain stable

**Guarantee 2: TLS Security**
- All public endpoints MUST use HTTPS
- TLS certificates MUST be valid (not expired, not self-signed)
- Certificate renewal MUST be automatic (no manual intervention)

**Guarantee 3: Routing Integrity**
- Requests to public endpoints MUST reach OAuth server unchanged
- HTTP headers MUST be preserved (especially Authorization header)
- Request body MUST be preserved for POST requests
- Query parameters MUST be preserved for GET requests

**Guarantee 4: Response Fidelity**
- OAuth server responses MUST reach client unchanged
- HTTP status codes MUST be preserved
- Response headers MUST be preserved (especially Set-Cookie, Location)
- Response body MUST be preserved (JSON, HTML)

**Guarantee 5: Error Transparency**
- Infrastructure errors (Funnel down, container down) MUST return 503 Service Unavailable
- Routing errors (no route to container) MUST return 502 Bad Gateway
- OAuth errors (invalid request) MUST return OAuth-compliant error responses

## Request Transformation Contract

### No Transformation (Pass-Through)

**Request Components That MUST NOT Be Modified**:
- HTTP method (GET, POST, PUT, DELETE)
- Request path (except routing prefix removal)
- Query parameters
- Request body (raw bytes preserved)
- Most HTTP headers

**Example - Authorization Request**:

**Public Request**:
```http
GET /alexa/authorize?client_id=ABC&response_type=code&... HTTP/1.1
Host: a0d7b954-tailscale.ts.net
User-Agent: Amazon-Alexa/1.0
```

**Forwarded to Music Assistant** (MUST preserve):
```http
GET /alexa/authorize?client_id=ABC&response_type=code&... HTTP/1.1
Host: music-assistant:8096  # Only Host header changes
User-Agent: Amazon-Alexa/1.0
X-Forwarded-For: [original client IP]  # Added by proxy
X-Forwarded-Proto: https  # Added by proxy
```

### Permitted Header Additions

**Headers Proxy MAY Add**:
- `X-Forwarded-For`: Original client IP address
- `X-Forwarded-Proto`: Original protocol (https)
- `X-Forwarded-Host`: Original host (a0d7b954-tailscale.ts.net)
- `X-Real-IP`: Client IP address

**Headers Proxy MUST Preserve**:
- `Authorization`: OAuth credentials
- `Content-Type`: Request body format
- `Accept`: Client preferences
- `User-Agent`: Client identification
- `Referer`: Origin tracking

**Headers Proxy SHOULD Remove** (security):
- `X-Forwarded-For`: If already present (prevent spoofing)
- Internal Tailscale routing headers

## Response Transformation Contract

### Minimal Transformation

**Response Components That MUST NOT Be Modified**:
- HTTP status code
- Response body (raw bytes preserved)
- OAuth-specific headers (Location, Set-Cookie)
- Content headers (Content-Type, Content-Length)

**Example - Token Response**:

**Music Assistant Response**:
```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 123

{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Public Response** (MUST preserve):
```http
HTTP/1.1 200 OK
Content-Type: application/json
Content-Length: 123
X-Served-By: Tailscale  # Optional addition

{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Error Response Contract

**Infrastructure Errors**:

**When Funnel is down**:
```http
HTTP/1.1 503 Service Unavailable
Content-Type: application/json

{
  "error": "service_unavailable",
  "error_description": "Tailscale Funnel is not available"
}
```

**When Music Assistant is unreachable**:
```http
HTTP/1.1 502 Bad Gateway
Content-Type: application/json

{
  "error": "bad_gateway",
  "error_description": "OAuth server is not responding"
}
```

**When routing fails**:
```http
HTTP/1.1 502 Bad Gateway
Content-Type: application/json

{
  "error": "bad_gateway",
  "error_description": "Unable to route request to OAuth server"
}
```

**OAuth Errors** (MUST pass through from OAuth server):
```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "error": "invalid_client",
  "error_description": "Client authentication failed"
}
```

## Routing Configuration Contract

### Path Routing Rules

**Rule 1: Health Check**
- Public path: `/health`
- Internal path: `/health`
- Transformation: None (direct pass-through)

**Rule 2: Alexa Authorization**
- Public path: `/alexa/authorize`
- Internal path: `/alexa/authorize`
- Transformation: None (direct pass-through)

**Rule 3: Alexa Token**
- Public path: `/alexa/token`
- Internal path: `/alexa/token`
- Transformation: None (direct pass-through)

**Rule 4: Catch-All**
- Public path: `/*` (any other path)
- Response: `404 Not Found`

### Protocol Downgrade Contract

**Public Side** (TLS-encrypted):
- Protocol: HTTPS
- Port: 443
- Encryption: TLS 1.2+
- Certificate: Tailscale-managed

**Internal Side** (plaintext acceptable):
- Protocol: HTTP
- Port: 8096
- Encryption: None (traffic within Docker network)
- Justification: Traffic never leaves Docker bridge network

**Security Rationale**:
- Docker bridge network is isolated from external access
- Traffic between containers is trusted
- TLS encryption overhead unnecessary for local traffic
- Simplified troubleshooting (can inspect traffic with tcpdump)

**Alternative** (if paranoid security required):
- Internal protocol could be upgraded to HTTPS
- Would require Music Assistant to generate TLS certificate
- Adds complexity without meaningful security benefit

## Performance Contract

### Latency Budget

**Total Latency**: < 2 seconds (end-to-end for authorization flow)

**Breakdown**:
- Tailscale Funnel overhead: < 50ms
- TLS termination: < 50ms
- Reverse proxy forwarding: < 50ms
- Docker network routing: < 10ms
- OAuth server processing: < 1800ms
- Return path (same routing): < 50ms

**Monitoring Points**:
- Measure latency at Funnel entry (external client → Funnel)
- Measure latency at proxy (Funnel → Music Assistant)
- Measure latency at OAuth server (processing time)

### Throughput Contract

**Expected Load**:
- Authorization requests: < 10 per hour (human-initiated)
- Token requests: < 20 per hour (includes refreshes)
- Health checks: < 60 per hour (monitoring)

**Capacity Requirements**:
- Funnel capacity: > 1000 requests/hour (Tailscale SLA)
- Reverse proxy capacity: > 500 requests/hour
- OAuth server capacity: > 100 requests/hour

**No Rate Limiting Required**:
- OAuth flow is naturally rate-limited (human interaction)
- Health checks are infrequent
- If abuse detected, rate limiting can be added without breaking contract

### Availability Contract

**Target Availability**: 99.9% (43 minutes downtime per month)

**Dependency Chain**:
- Tailscale Funnel availability: 99.9% (Tailscale SLA)
- HABoxHill host uptime: 99.9% (assumed)
- Tailscale container uptime: 99.9% (managed by HA)
- Music Assistant container uptime: 99.9% (managed by HA)

**Combined Availability**: ~99.6% (multiple dependencies)

**Acceptable Downtime Scenarios**:
- Scheduled maintenance (announced 24 hours in advance)
- Container restarts (< 30 seconds)
- Home Assistant updates (< 5 minutes)

## Security Contract

### TLS Requirements

**Minimum TLS Version**: TLSv1.2
**Preferred TLS Version**: TLSv1.3
**Cipher Suites**: Modern, secure ciphers only (no RC4, no MD5)
**Certificate Validation**: MUST use valid, trusted certificates (Tailscale CA)

**Certificate Renewal**:
- Automatic renewal before expiration
- No manual intervention required
- Graceful rollover (no downtime)

### Authentication Passthrough

**OAuth Client Credentials**:
- Passed via `Authorization` header (Basic auth)
- MUST be preserved by proxy
- MUST NOT be logged or stored by proxy

**OAuth Access Tokens**:
- Passed via query parameter or POST body
- MUST be preserved by proxy
- MUST NOT be logged or stored by proxy

**Security Headers**:
- Proxy SHOULD add security headers (HSTS, X-Frame-Options)
- Proxy MUST NOT strip security headers from OAuth server

### Access Control

**Who Can Access Public Endpoints**:
- Any client with valid OAuth credentials
- Amazon Alexa service (primary use case)
- User's browser (during authorization flow)
- Monitoring tools (health check only)

**Who Cannot Access Public Endpoints**:
- No IP-based restrictions (Alexa IPs vary)
- No geographic restrictions
- No user-agent restrictions

**Tailscale ACLs** (optional additional layer):
- Can restrict access to specific Tailscale nodes (if needed)
- Should NOT be used for OAuth (breaks Alexa access)
- Can be used for health check monitoring

## Failure Modes and Handling

### Failure Mode 1: Tailscale Funnel Unavailable

**Symptoms**:
- Public URL returns connection timeout
- Cannot reach `https://a0d7b954-tailscale.ts.net`

**Client Impact**: Complete service outage (OAuth flow fails)

**Detection**:
- External monitoring (uptime check on public URL)
- Tailscale Funnel status: `tailscale funnel status`

**Recovery**:
- Restart Tailscale Funnel: `tailscale funnel on 8096`
- Restart Tailscale container: `docker restart addon_a0d7b954_tailscale`
- Contact Tailscale support (if infrastructure issue)

**Fallback**: Nabu Casa proxy (alternative public endpoint)

### Failure Mode 2: Reverse Proxy Misconfiguration

**Symptoms**:
- Public URL returns 502 Bad Gateway
- Funnel works but cannot reach Music Assistant

**Client Impact**: Complete service outage (OAuth flow fails)

**Detection**:
- 502 errors in Tailscale logs
- Cannot reach Music Assistant from Tailscale container:
  ```bash
  docker exec addon_a0d7b954_tailscale wget http://music-assistant:8096/health
  ```

**Recovery**:
- Verify Music Assistant is running: `docker ps | grep music-assistant`
- Verify OAuth server is listening: `curl http://localhost:8096/health`
- Reconfigure Funnel routing (see operations guide)

### Failure Mode 3: OAuth Server Down

**Symptoms**:
- Public URL returns 502 Bad Gateway
- Music Assistant container is down or not responding

**Client Impact**: Complete service outage (OAuth flow fails)

**Detection**:
- Music Assistant container not in `docker ps` output
- Health check fails: `curl http://localhost:8096/health`

**Recovery**:
- Restart Music Assistant container
- Check Music Assistant logs for crash reason
- Verify OAuth server module loaded

### Failure Mode 4: TLS Certificate Expired

**Symptoms**:
- Browsers show certificate warning
- Alexa rejects connection (TLS validation fails)

**Client Impact**: Complete service outage (OAuth flow fails)

**Detection**:
- Certificate warning in browser
- Check certificate expiry: `curl -vI https://a0d7b954-tailscale.ts.net 2>&1 | grep expire`

**Recovery**:
- Should auto-renew (Tailscale manages certificates)
- If manual renewal needed: Restart Tailscale Funnel
- Contact Tailscale support (if auto-renewal fails)

### Failure Mode 5: Network Routing Failure

**Symptoms**:
- Tailscale container cannot reach Music Assistant
- Docker bridge network issue

**Client Impact**: Complete service outage (OAuth flow fails)

**Detection**:
- `docker exec addon_a0d7b954_tailscale ping music-assistant` fails
- `docker network inspect bridge` shows issues

**Recovery**:
- Restart Docker daemon
- Restart both containers
- Check Docker network configuration

## Contract Testing Procedures

### Test 1: Public Endpoint Accessibility

**Purpose**: Verify public URLs are reachable from internet

**Procedure** (from external network, not on Tailscale):
```bash
# Test health endpoint
curl -v https://a0d7b954-tailscale.ts.net/health

# Expected: 200 OK with JSON {"status":"ok", ...}
```

**Success Criteria**:
- HTTP status: 200 OK
- Response time: < 2 seconds
- Valid JSON response
- TLS certificate valid

### Test 2: OAuth Authorization Flow

**Purpose**: Verify complete OAuth flow works end-to-end

**Procedure**:
```bash
# Step 1: Request authorization
curl -v "https://a0d7b954-tailscale.ts.net/alexa/authorize?client_id=test&response_type=code&redirect_uri=https://example.com/callback"

# Expected: 200 OK with HTML authorization page

# Step 2: Simulate user approval (requires browser or automation)
# [Manual step - user approves in browser]

# Step 3: Exchange code for token
curl -v -X POST https://a0d7b954-tailscale.ts.net/alexa/token \
  -H "Authorization: Basic [base64 credentials]" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=AUTH_CODE&redirect_uri=https://example.com/callback"

# Expected: 200 OK with JSON {"access_token": ..., "refresh_token": ...}
```

**Success Criteria**:
- All requests complete successfully
- Headers preserved correctly
- Redirect flow works
- Tokens issued correctly

### Test 3: Header Preservation

**Purpose**: Verify critical headers pass through proxy

**Procedure**:
```bash
# Send request with custom headers
curl -v https://a0d7b954-tailscale.ts.net/health \
  -H "User-Agent: Test-Client/1.0" \
  -H "X-Custom-Header: Test" \
  -H "Authorization: Bearer test-token"

# Check Music Assistant logs to verify headers received
docker logs music-assistant | tail -20
```

**Success Criteria**:
- User-Agent preserved
- Authorization header preserved
- X-Forwarded-For added (client IP)
- X-Forwarded-Proto added (https)

### Test 4: Error Response Handling

**Purpose**: Verify error responses return correctly

**Procedure**:
```bash
# Test 404 for non-existent endpoint
curl -v https://a0d7b954-tailscale.ts.net/nonexistent

# Expected: 404 Not Found

# Test 401 for invalid OAuth request
curl -v -X POST https://a0d7b954-tailscale.ts.net/alexa/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code"  # Missing required params

# Expected: 401 Unauthorized with OAuth error JSON
```

**Success Criteria**:
- Correct HTTP status codes
- Error messages preserved from OAuth server
- No proxy-specific errors mixed in

### Test 5: Performance Under Load

**Purpose**: Verify routing performs within latency budget

**Procedure**:
```bash
# Run 100 health checks and measure latency
for i in {1..100}; do
  curl -w "@curl-format.txt" -o /dev/null -s https://a0d7b954-tailscale.ts.net/health
done | awk '{sum+=$1; count++} END {print "Average:", sum/count "ms"}'

# curl-format.txt contents:
# time_total:%{time_total}\n
```

**Success Criteria**:
- Average latency: < 500ms
- 95th percentile: < 1000ms
- No timeouts
- No 502/503 errors

## Contract Versioning and Changes

### Version 1.0 (Current)

**Established**: 2025-10-25
**Public Base URL**: `https://a0d7b954-tailscale.ts.net`
**Endpoints**: `/health`, `/alexa/authorize`, `/alexa/token`

### Future Changes (Backward Compatibility)

**Allowed Changes** (non-breaking):
- Add new endpoints (e.g., `/alexa/revoke`)
- Add optional query parameters
- Add optional request headers
- Add response headers
- Improve performance (reduce latency)
- Improve availability (increase uptime)

**Prohibited Changes** (breaking):
- Change public base URL without redirect
- Remove or rename existing endpoints
- Change required parameters
- Change response format (JSON structure)
- Remove required response headers
- Downgrade security (TLS version, cipher suites)

### Change Notification

**If breaking change required**:
1. Announce 90 days in advance
2. Provide migration guide
3. Offer dual support (old + new) for 90 days
4. Redirect old URLs to new URLs
5. Update Alexa skill configuration

## Monitoring and Observability

### Health Check Monitoring

**External Monitoring** (recommended):
- Service: UptimeRobot, Pingdom, or similar
- URL: `https://a0d7b954-tailscale.ts.net/health`
- Frequency: Every 5 minutes
- Alert on: > 2 consecutive failures

**Internal Monitoring**:
```bash
# Cron job to check health every minute
* * * * * curl -f http://localhost:8096/health || logger "OAuth server health check failed"
```

### Metrics to Track

**Request Metrics**:
- Total requests per endpoint (health, authorize, token)
- Request duration (p50, p95, p99)
- Error rate (4xx, 5xx)
- Success rate (2xx)

**Infrastructure Metrics**:
- Tailscale Funnel uptime
- Tailscale container uptime
- Music Assistant container uptime
- Docker bridge network status

**Security Metrics**:
- Failed authentication attempts
- Invalid token requests
- TLS handshake failures
- Certificate expiry countdown

### Logging Requirements

**Access Logs** (proxy layer):
```
[timestamp] [client_ip] [method] [path] [status] [duration]
2025-10-25T20:00:00Z 1.2.3.4 GET /health 200 45ms
```

**Error Logs** (proxy layer):
```
[timestamp] [level] [message]
2025-10-25T20:05:00Z ERROR Failed to connect to music-assistant:8096: connection refused
```

**OAuth Logs** (Music Assistant):
```
[timestamp] [level] [client_id] [action] [result]
2025-10-25T20:10:00Z INFO alexa-skill-123 authorization_requested approved
```

**Security Note**: MUST NOT log sensitive data:
- Client secrets
- Access tokens
- Refresh tokens
- Authorization codes
- User passwords

## See Also

- [ALEXA_OAUTH_ENDPOINTS_CONTRACT](ALEXA_OAUTH_ENDPOINTS_CONTRACT.md) - OAuth API specification
- [HABOXHILL_NETWORK_TOPOLOGY](../04_INFRASTRUCTURE/HABOXHILL_NETWORK_TOPOLOGY.md) - Infrastructure implementation
- [HOME_ASSISTANT_CONTAINER_TOPOLOGY](../02_REFERENCE/HOME_ASSISTANT_CONTAINER_TOPOLOGY.md) - Container reference
- [TAILSCALE_FUNNEL_CONFIGURATION_HA](../05_OPERATIONS/TAILSCALE_FUNNEL_CONFIGURATION_HA.md) - Setup procedures
- [ALEXA_OAUTH_SETUP_PROGRESS](../05_OPERATIONS/ALEXA_OAUTH_SETUP_PROGRESS.md) - Current status
