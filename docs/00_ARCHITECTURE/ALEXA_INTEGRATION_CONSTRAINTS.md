# Alexa Integration Architectural Constraints
**Purpose**: Document fundamental architectural constraints that make Alexa integration with Music Assistant complex
**Audience**: Architects, decision-makers, anyone evaluating Alexa integration feasibility
**Layer**: 00_ARCHITECTURE (technology-agnostic principles)
**Related**:
- [Platform Invariants](PLATFORM_INVARIANTS.md)
- [Integration Principles](INTEGRATION_PRINCIPLES.md)

---

## Intent

This document explains **why** exposing Music Assistant to the public internet is an architectural requirement for Alexa integration, independent of any specific implementation technology. This is not about how to do it (Layer 04/05), but about the fundamental constraints that make it necessary.

## Problem Statement

**Goal**: Enable Amazon Alexa devices to play music from a Music Assistant server using account linking.

**Core Constraint**: Amazon Alexa's account linking architecture **requires** OAuth endpoints to be publicly accessible on the internet with valid HTTPS certificates, and these endpoints **must** be directly accessible by:
1. Amazon's Alexa service (for OAuth token exchange)
2. End users' web browsers (for OAuth authorization flow)
3. Amazon's certificate validation services (TLS verification)

**Why This Matters**: This is not a configuration choice or implementation detail. It is a fundamental architectural requirement imposed by Amazon's security and authentication model.

## Architectural Constraints

### 1. OAuth Flow Requirements (Non-Negotiable)

**Constraint**: The OAuth 2.0 authorization code flow requires three publicly accessible endpoints:

```
/authorize  - User browser must reach this for login/consent
/token      - Alexa service must reach this for token exchange
/callback   - Alexa service redirects here after authorization
```

**Why Public Access Required**:
- **User browser access**: End users access `/authorize` from arbitrary networks (home, mobile, work) outside the home network
- **Alexa service access**: Amazon's cloud services initiate token requests from Amazon's infrastructure
- **No VPN/tunnel option**: Neither users nor Amazon services can be required to join a private network
- **Real-time interaction**: OAuth flow is synchronous; proxies/relays introduce points of failure

**Why This Can't Be Proxied Through HA Cloud**:
- OAuth requires direct endpoint access for security validation
- Redirect URIs must exactly match registered values
- TLS certificate must match the domain serving endpoints
- Token exchange happens server-to-server (Alexa → Music Assistant)

### 2. TLS Certificate Validation Requirements

**Constraint**: Amazon validates TLS certificates against the OAuth endpoint hostname.

**Requirements**:
- Certificate must be from a publicly trusted Certificate Authority
- Certificate subject/SAN must match the hostname users/Alexa access
- Certificate must be valid (not expired, not self-signed)
- No certificate pinning bypass options available

**Why This Matters**:
- Self-signed certificates: **Not accepted** by Alexa
- Internal CA certificates: **Not trusted** by Alexa
- Certificate-hostname mismatch: **Rejected** by Alexa
- Localhost/private IPs: **Invalid** for OAuth endpoints

**Implication**: Any solution must provide valid publicly-trusted HTTPS.

### 3. Home Assistant Integration Insufficiency

**Why HA's Native Alexa Integration Doesn't Solve This**:

HA's Alexa integration is designed for **device control** (smart home), not **media streaming authentication**:

- **HA Alexa Cloud Integration**: Exposes HA entities (switches, lights, sensors) to Alexa
- **What it does**: Allows "Alexa, turn on living room light" (HA entity control)
- **What it doesn't do**: Provide OAuth endpoints for third-party service authentication
- **Architecture**: HA → Nabu Casa Cloud ← Alexa (for entity control only)

**Music Assistant's Requirement**: OAuth-based account linking for media streaming services
- Music Assistant is not an HA entity
- Alexa needs to authenticate directly with Music Assistant's OAuth provider
- HA Cloud cannot proxy OAuth flows for external services

**Why Nabu Casa Custom Domain Doesn't Work**:
- Nabu Casa provides domain + TLS for HA web interface (port 443)
- Music Assistant runs on port 8096 (separate service)
- Nabu Casa does **not** proxy arbitrary ports (only 443 for HA)
- Testing confirmed: Custom domain at `:8096` is blocked/unreachable

### 4. Direct Public Exposure Requirement

**Fundamental Constraint**: At least one of these must be true:

1. Music Assistant endpoint is directly reachable from public internet (port forward)
2. A publicly accessible proxy/tunnel terminates TLS and forwards to Music Assistant
3. A publicly accessible service provides OAuth on Music Assistant's behalf

**Why This Is Unavoidable**:
- Amazon controls the OAuth client (Alexa skill)
- Amazon defines where OAuth endpoints must be
- Users and Amazon services must reach the same endpoints
- No intermediate authentication layer is permitted in OAuth flow

### 5. Home Network vs Internet Boundary

**The Core Tension**:

**Private Network Reality**:
- Music Assistant runs inside home network (HA Add-on)
- Home network is behind NAT/firewall (private IP space)
- Direct access from internet is blocked by default (security best practice)

**Alexa's Requirement**:
- Alexa service runs in Amazon's cloud (public internet)
- OAuth endpoints must be internet-accessible
- No exceptions for private/home deployments

**Architectural Implication**: Any solution must bridge this boundary while maintaining security.

## Why This Isn't a Simple Integration Problem

### Misconception: "Just Use HA's Alexa Integration"
**Reality**: HA's Alexa integration is for smart home control, not OAuth-based service authentication. They solve different problems.

### Misconception: "Use a VPN/Tunnel for Security"
**Reality**: OAuth endpoints must be publicly accessible for user browsers and Amazon's services. Neither can be required to join a VPN.

### Misconception: "Self-Signed Certificates Are Fine"
**Reality**: Amazon's OAuth implementation requires publicly trusted certificates. Self-signed certificates are rejected.

### Misconception: "Nabu Casa Solves This"
**Reality**: Nabu Casa provides HA Cloud integration (port 443 only) and custom domains. It does not proxy arbitrary services on custom ports.

### Misconception: "Just Disable TLS Validation"
**Reality**: Amazon controls the Alexa OAuth client. TLS validation cannot be disabled by the user.

## Fundamental Trade-Offs

Any solution to these constraints involves trade-offs:

**Security vs Accessibility**:
- Exposing services publicly increases attack surface
- OAuth requires public accessibility
- Trade-off: Minimize exposure while meeting requirements

**Simplicity vs Control**:
- Managed services (Nabu Casa, Tailscale Funnel) are simple but limit control
- Direct exposure is complex but provides full control
- Trade-off: Operational complexity vs architectural flexibility

**Cost vs Capability**:
- Some solutions require subscriptions (Nabu Casa, Tailscale, domain + DynDNS)
- Free solutions may have limitations (port forwarding alone)
- Trade-off: Recurring costs vs one-time complexity

## Verification Questions

To verify any proposed solution respects these constraints:

1. **Can an arbitrary user's web browser reach the OAuth `/authorize` endpoint?**
   - If no → OAuth flow fails at user consent step

2. **Can Amazon's Alexa service reach the `/token` endpoint from Amazon's infrastructure?**
   - If no → OAuth flow fails at token exchange step

3. **Does the TLS certificate match the hostname and come from a public CA?**
   - If no → Amazon rejects the connection (certificate validation failure)

4. **Does the solution expose only required endpoints, not the entire Music Assistant interface?**
   - If no → Unnecessary attack surface exposed

5. **Is the solution maintainable with reasonable operational burden?**
   - If no → Solution will degrade or fail over time

## Architectural Principles Derived

From these constraints, we derive principles for any valid solution:

1. **Public Accessibility**: OAuth endpoints must be reachable from public internet
2. **Valid HTTPS**: TLS certificates must be publicly trusted and match hostname
3. **Minimal Exposure**: Expose only required endpoints, not entire service
4. **Defense in Depth**: Public exposure requires additional security layers
5. **Failure Transparency**: OAuth failures must be observable and debuggable
6. **Operational Sustainability**: Solution must be maintainable long-term

## Related Constraints

These architectural constraints interact with:

- **Network Security** (firewall rules, attack surface)
- **Certificate Management** (renewal, validation, trust chains)
- **DNS Management** (hostname resolution, dynamic DNS)
- **Service Discovery** (how Alexa finds the OAuth endpoints)
- **Home Network Architecture** (NAT, router capabilities)

## See Also

- **[Music Assistant Alexa Public Interface](../03_INTERFACES/MUSIC_ASSISTANT_ALEXA_PUBLIC_INTERFACE.md)** - The contract Alexa requires
- **[Alexa Public Exposure Options](../04_INFRASTRUCTURE/ALEXA_PUBLIC_EXPOSURE_OPTIONS.md)** - Tested implementation approaches
- **[Viable Implementation Paths](../05_OPERATIONS/MUSIC_ASSISTANT_ALEXA_VIABLE_PATHS.md)** - Concrete procedures
