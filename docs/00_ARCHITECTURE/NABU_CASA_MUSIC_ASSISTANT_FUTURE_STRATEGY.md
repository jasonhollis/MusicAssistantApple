# Nabu Casa + Music Assistant Future Architecture Strategy
**Purpose**: Technology-agnostic principles for unified authentication architecture
**Audience**: Architects, long-term planning
**Layer**: 00_ARCHITECTURE (abstract principles, no specific technologies)
**Related**:
- [Alexa Integration Constraints](ALEXA_INTEGRATION_CONSTRAINTS.md) - Current state challenges
- [Future Implementation Work](../04_INFRASTRUCTURE/NABU_CASA_MUSIC_ASSISTANT_FUTURE_WORK.md) - Concrete implementation paths
- [Future Migration Plan](../05_OPERATIONS/NABU_CASA_MUSIC_ASSISTANT_FUTURE_PLAN.md) - Operational transition procedures

---

## Intent

This document defines the **architectural principles** for a future unified authentication system that integrates Music Assistant with Home Assistant's Nabu Casa cloud services. This represents the **ideal end state** that current interim solutions (like Tailscale Funnel) should eventually migrate toward.

This document is **technology-agnostic** - it describes WHAT the system should achieve and WHY, not HOW to implement it.

---

## Current State: Why This Matters

**Problem**: Music Assistant requires public OAuth endpoints for Alexa integration, but current architecture has no integrated solution.

**Current Workarounds**:
- Tailscale Funnel (external dependency, subscription cost)
- Manual port forwarding (security risk, complex certificate management)
- Cloudflare Tunnel (external dependency, corporate reliance)

**Fundamental Issue**: Music Assistant authentication is separate from Home Assistant authentication, requiring separate public exposure mechanisms.

**Impact**:
- Increased complexity (multiple auth systems)
- External dependencies (Tailscale, Cloudflare)
- Higher operational burden (monitoring multiple services)
- Inconsistent user experience (different auth flows)
- Community sustainability concerns (reliance on commercial services)

---

## Future State: Unified Authentication Architecture

### Core Principle: Single Point of Authentication

**Principle**: All services within the Home Assistant ecosystem should authenticate through a **single unified authentication system**.

**Why This Matters**:
- **Simplicity**: One auth system to configure, monitor, and maintain
- **Security**: Centralized auth enforcement, audit logging, access control
- **User Experience**: Consistent authentication flow across all services
- **Integration**: Seamless service-to-service authentication
- **Sustainability**: Community-funded infrastructure (Nabu Casa)

**Application to Music Assistant**:
- Music Assistant authentication flows through Home Assistant's auth system
- Alexa account linking uses Home Assistant's OAuth provider (exposed via Nabu Casa)
- No separate public exposure needed for Music Assistant
- Single point of access control for all HA services

---

### Principle 1: Cloud Gateway Should Proxy All External Access

**Principle**: External access to local services should flow through a single cloud gateway.

**Current Reality**:
- Home Assistant exposed via Nabu Casa cloud
- Music Assistant exposed via separate mechanism (Tailscale/other)

**Future State**:
- All external access flows through Nabu Casa cloud
- Nabu Casa proxies requests to appropriate local services
- Single TLS termination point
- Centralized DDoS protection, rate limiting, abuse prevention

**Why This Matters**:
- **Security**: Single hardened entry point instead of multiple attack surfaces
- **Reliability**: Professional SLA from Nabu Casa instead of best-effort from multiple providers
- **Simplicity**: One service to monitor instead of multiple tunnels/proxies
- **Performance**: Optimized routing from edge locations

**Implementation Options** (see Infrastructure layer for details):
- Nabu Casa supports custom service routing (Path 2 in Future Work)
- Music Assistant becomes HA integration using HA auth (Path 1 in Future Work)
- Music Assistant provides native Alexa skill with own cloud (Path 3 in Future Work)

---

### Principle 2: Authentication Should Be Identity-Based, Not Service-Based

**Principle**: Users authenticate to an **identity**, not individual services.

**Current Reality**:
- User has Home Assistant credentials
- User has separate Music Assistant credentials (if MA has auth)
- Alexa links to Music Assistant specifically

**Future State**:
- User has single Home Assistant identity
- Music Assistant uses HA identity for access control
- Alexa links to Home Assistant identity
- Music Assistant is authorized service within that identity

**Why This Matters**:
- **User Experience**: Single login for all services
- **Security**: Centralized password policy, MFA, session management
- **Access Control**: Unified permission model across all services
- **Auditability**: Single audit log for all authentication events

**Application to Alexa**:
- Alexa account links to "Home Assistant" identity
- Music Assistant is a service available within that identity
- User grants Alexa permission to access "Music Assistant service" within HA
- Revocation of HA access revokes all service access (including Music Assistant)

---

### Principle 3: External Services Should Use Standardized Protocols

**Principle**: External integrations (like Alexa) should use **industry-standard protocols** (OAuth 2.0, OpenID Connect).

**Current Reality**:
- Music Assistant implements OAuth 2.0 server
- Alexa implements OAuth 2.0 client
- **But**: OAuth server is custom Music Assistant implementation

**Future State**:
- Home Assistant provides centralized OAuth 2.0 server
- Music Assistant registers as OAuth scope within HA's OAuth server
- Alexa connects to HA's OAuth server
- HA OAuth server delegates Music Assistant access control to MA

**Why This Matters**:
- **Interoperability**: Any OAuth 2.0 client can integrate (not just Alexa)
- **Security**: Well-tested OAuth implementation in HA core
- **Maintainability**: OAuth complexity handled by HA, not individual add-ons
- **Standards Compliance**: Proper PKCE, state validation, refresh tokens

**Delegation Model**:
```
Alexa (OAuth Client)
  ↓ OAuth flow
Home Assistant (OAuth Server)
  ↓ Scope: music_assistant.read, music_assistant.control
Music Assistant (Resource Server)
  ↓ Validates HA-issued access token
Music Assistant API
```

---

### Principle 4: Cloud Services Should Be Community-Funded

**Principle**: Infrastructure relied upon by the community should be **funded by the community**.

**Current Reality**:
- Home Assistant cloud: Nabu Casa (community-funded, $6.50/month)
- Music Assistant public exposure: Various commercial options (Tailscale, Cloudflare)

**Future State**:
- All critical infrastructure funded through Nabu Casa subscription
- No dependence on venture-capital-backed commercial services for core functionality
- Community has control over infrastructure sustainability

**Why This Matters**:
- **Sustainability**: Direct funding for development and infrastructure
- **Alignment**: Service provider incentivized to serve users, not investors
- **Resilience**: Community can fork/maintain if needed
- **Ethics**: Support for open-source values

**Decision Criteria**:
- Prefer Nabu Casa for production deployments (supports community)
- Accept commercial services for interim/testing only
- Avoid architectural decisions that lock-in commercial dependencies

---

### Principle 5: Failure Modes Should Gracefully Degrade

**Principle**: Cloud service outages should not break local functionality.

**Current Reality**:
- If Nabu Casa down: HA remote access unavailable
- If Tailscale down: Music Assistant OAuth unavailable (breaks Alexa)

**Future State**:
- If Nabu Casa down: HA remote access unavailable, BUT local access still works
- If Nabu Casa down: Alexa integration unavailable, BUT local Music Assistant works
- Cloud services are **convenience layer**, not **critical dependency**

**Why This Matters**:
- **Resilience**: Home automation continues during internet/cloud outages
- **Privacy**: Critical functions don't require cloud
- **Control**: User retains local control even if cloud provider fails

**Design Implications**:
- Local authentication always works (LAN access)
- Cloud authentication is additive (enables remote access)
- Services degrade gracefully when cloud unavailable
- Clear separation between local and remote capabilities

---

## Architectural Patterns for Future Implementation

### Pattern 1: Service Integration (Preferred)

**Description**: Music Assistant becomes first-class Home Assistant integration.

**Architecture**:
```
User ←→ Home Assistant (UI/Auth)
           ↓
       Music Assistant Integration
           ↓
       Music Player (local)
```

**OAuth Flow**:
```
Alexa → HA OAuth Server → HA Auth → Music Assistant Integration
```

**Benefits**:
- Single authentication system
- Native HA UI integration
- Unified configuration
- Community-funded infrastructure (Nabu Casa)

**Trade-offs**:
- Requires Music Assistant architectural changes
- Tighter coupling to HA ecosystem
- Less flexibility for non-HA deployments

**Applicability**: Best for users committed to Home Assistant ecosystem.

---

### Pattern 2: Cloud Proxy with Custom Service Support

**Description**: Nabu Casa adds support for proxying custom service endpoints.

**Architecture**:
```
User ←→ Nabu Casa Cloud ←→ Home Assistant ←→ Music Assistant (separate service)
```

**OAuth Flow**:
```
Alexa → Nabu Casa Proxy → Music Assistant OAuth Server
```

**Benefits**:
- Maintains Music Assistant independence
- Uses Nabu Casa infrastructure
- Community-funded
- Simpler than full integration

**Trade-offs**:
- Nabu Casa must implement custom service routing
- Still requires separate Music Assistant auth (not unified with HA)
- Complexity in routing configuration

**Applicability**: Bridge solution if full integration not feasible.

---

### Pattern 3: Native Cloud Service

**Description**: Music Assistant provides official cloud service with native Alexa skill.

**Architecture**:
```
User ←→ Music Assistant Cloud ←→ Music Assistant (local)
Alexa ←→ Music Assistant Cloud (OAuth)
```

**OAuth Flow**:
```
Alexa → Music Assistant Cloud OAuth → Local Music Assistant
```

**Benefits**:
- Purpose-built for Music Assistant use cases
- Professional OAuth implementation
- Optimized for music streaming

**Trade-offs**:
- Requires Music Assistant to operate cloud infrastructure
- Additional subscription cost (or ads/freemium model)
- Not community-funded through Nabu Casa
- Separate from HA ecosystem

**Applicability**: If Music Assistant becomes standalone product with commercial support.

---

## Quality Attributes for Future Architecture

### Security

**Requirements**:
- Centralized authentication (single identity provider)
- OAuth 2.0 with PKCE (protection against auth code interception)
- TLS 1.3 minimum (strong encryption)
- Regular security audits (HA core standards)
- Credential rotation support (refresh tokens)

**Verification**:
- Penetration testing of OAuth flow
- Security audit by HA security team
- Community security review
- Automated vulnerability scanning

---

### Reliability

**Requirements**:
- 99.9% uptime SLA (Nabu Casa standard)
- Graceful degradation on cloud outage
- Automatic reconnection on network restore
- Health monitoring and alerting

**Verification**:
- Chaos engineering tests (simulate cloud outage)
- Load testing OAuth endpoints
- Long-running stability tests (30+ days)
- Mean-time-to-recovery measurement

---

### Usability

**Requirements**:
- Single authentication flow (no separate Music Assistant login)
- Clear authorization prompts (what Alexa can access)
- Easy account linking (3-4 steps maximum)
- Intuitive error messages (actionable guidance)

**Verification**:
- User testing with non-technical users
- Time-to-first-success measurement
- Error recovery testing
- Accessibility compliance (WCAG 2.1)

---

### Maintainability

**Requirements**:
- Centralized OAuth implementation (no per-service OAuth)
- Standard protocols (OAuth 2.0, OpenID Connect)
- Comprehensive logging (OAuth events, errors)
- Documented troubleshooting procedures

**Verification**:
- Code review by HA core maintainers
- Documentation review
- Support ticket analysis (common issues)
- Mean-time-to-diagnosis measurement

---

### Performance

**Requirements**:
- OAuth flow completion < 5 seconds (end-to-end)
- Token refresh < 1 second
- Cloud proxy latency < 100ms added
- Supports 1000+ concurrent OAuth flows (per Nabu Casa instance)

**Verification**:
- Performance benchmarking
- Latency percentile analysis (p50, p95, p99)
- Load testing under concurrent users
- Geographic latency testing

---

### Sustainability

**Requirements**:
- Community-funded infrastructure (Nabu Casa)
- Open-source implementation (auditability)
- No vendor lock-in (standard protocols)
- Long-term maintenance commitment

**Verification**:
- Business model analysis (Nabu Casa sustainability)
- License review (OSI-approved)
- Protocol compliance testing (OAuth 2.0 spec)
- Community governance review

---

## Decision Framework for Migration

**When to migrate from interim solution to future architecture**:

### Trigger 1: Technical Capability Available

**Criteria**: One of the future implementation paths becomes technically feasible.

**Indicators**:
- Home Assistant core adds OAuth scope delegation
- Music Assistant releases as official HA integration
- Nabu Casa adds custom service routing
- Music Assistant launches official Alexa skill

**Decision**: Evaluate technical readiness, perform cost-benefit analysis, plan migration.

---

### Trigger 2: Interim Solution Becomes Unsustainable

**Criteria**: Current workaround fails or becomes prohibitively expensive/complex.

**Indicators**:
- Tailscale deprecates Funnel feature
- Tailscale pricing increases significantly
- Tailscale has extended outage
- Tailscale changes terms of service (unfavorable)

**Decision**: Accelerate migration to future architecture, or switch interim solutions.

---

### Trigger 3: User Requirements Change

**Criteria**: New requirements that interim solution cannot satisfy.

**Indicators**:
- Need for unified authentication (SSO)
- Compliance requirements (GDPR, SOC 2)
- Multi-tenant support needed
- Enterprise deployment requirements

**Decision**: Evaluate which future path best satisfies new requirements.

---

### Trigger 4: Community Consensus

**Criteria**: Home Assistant and Music Assistant communities align on approach.

**Indicators**:
- HA core team commits to OAuth scope delegation
- Music Assistant maintainers agree to HA integration approach
- Community votes on preferred path
- Architectural Decision Record (ADR) approved

**Decision**: Follow community consensus, contribute to implementation effort.

---

## Principles for Evaluating Future Proposals

When evaluating specific implementation proposals, apply these principles:

### 1. Does it reduce external dependencies?

**Goal**: Minimize reliance on third-party commercial services.

**Evaluation**:
- ✅ Good: Uses Nabu Casa (community-funded)
- ✅ Good: Runs entirely local (no cloud dependency)
- ⚠️ Acceptable: Uses commercial service as interim (with migration plan)
- ❌ Bad: Locks into commercial service permanently

---

### 2. Does it centralize authentication?

**Goal**: Single identity for all HA ecosystem services.

**Evaluation**:
- ✅ Good: Uses HA authentication system
- ⚠️ Acceptable: Delegates to HA auth (Music Assistant validates HA tokens)
- ⚠️ Acceptable: Separate auth with future migration path
- ❌ Bad: Permanent separate authentication system

---

### 3. Does it follow standard protocols?

**Goal**: Interoperability and long-term maintainability.

**Evaluation**:
- ✅ Good: OAuth 2.0 / OpenID Connect compliant
- ✅ Good: Uses well-tested libraries (Authlib, etc.)
- ⚠️ Acceptable: Custom protocol with clear specification
- ❌ Bad: Proprietary protocol without documentation

---

### 4. Does it degrade gracefully?

**Goal**: Local functionality preserved during cloud outages.

**Evaluation**:
- ✅ Good: Local access works always, cloud is additive
- ⚠️ Acceptable: Cloud required for remote access only
- ❌ Bad: Cloud required for basic functionality

---

### 5. Does it support community sustainability?

**Goal**: Fund open-source development and infrastructure.

**Evaluation**:
- ✅ Good: Uses Nabu Casa (directly funds HA development)
- ✅ Good: Self-hosted (no external funding required)
- ⚠️ Acceptable: Commercial interim with transition plan
- ❌ Bad: Permanent reliance on VC-backed commercial service

---

## Success Criteria for Future Architecture

The future architecture is successful when:

**✅ Single Authentication System**:
- User has one set of credentials for HA + Music Assistant
- Alexa account links to HA identity, not Music Assistant specifically
- Access control managed centrally in HA

**✅ Nabu Casa Integration**:
- All external access flows through Nabu Casa cloud
- No additional commercial services required (Tailscale, Cloudflare, etc.)
- Music Assistant OAuth accessible via Nabu Casa proxy

**✅ Standard Protocols**:
- OAuth 2.0 compliant (with PKCE)
- Supports refresh tokens (no re-authentication)
- Compatible with any OAuth 2.0 client (not Alexa-specific)

**✅ Graceful Degradation**:
- Local Music Assistant works during cloud outage
- Alexa integration unavailable, but local playback continues
- Clear user messaging when cloud unavailable

**✅ Community Sustainability**:
- Nabu Casa subscription supports HA development
- No dependence on commercial services for production
- Open-source implementation (auditability)

**✅ Operational Simplicity**:
- Single service to configure (HA + Nabu Casa)
- Single service to monitor (Nabu Casa status)
- Automatic certificate renewal (Nabu Casa handles)
- Zero manual maintenance for OAuth

---

## Non-Goals (Out of Scope)

This architecture strategy does NOT address:

**❌ Music Assistant Feature Development**: This is about authentication architecture, not music playback features.

**❌ Home Assistant Core Changes**: Assumes HA provides necessary OAuth capabilities (or will in future).

**❌ Alexa Skill Implementation**: Assumes Alexa skill exists; focuses on authentication only.

**❌ Multi-Cloud Support**: Focuses on Nabu Casa; other clouds out of scope.

**❌ Federation**: Assumes single HA instance; multi-instance federation not addressed.

---

## See Also

- **[Alexa Integration Constraints](ALEXA_INTEGRATION_CONSTRAINTS.md)** - Current state challenges that motivate this architecture
- **[Future Implementation Work](../04_INFRASTRUCTURE/NABU_CASA_MUSIC_ASSISTANT_FUTURE_WORK.md)** - Concrete technical implementation paths
- **[Future Migration Plan](../05_OPERATIONS/NABU_CASA_MUSIC_ASSISTANT_FUTURE_PLAN.md)** - Operational procedures for transitioning to future architecture
- **[Current Interim Implementation](../05_OPERATIONS/TAILSCALE_FUNNEL_IMPLEMENTATION_ALEXA.md)** - Current working solution

---

## Document History

**Version**: 1.0
**Status**: DRAFT - Architectural vision, not yet implemented
**Review Date**: When HA OAuth scope delegation or Music Assistant HA integration becomes available
**Maintainer**: Project architects and HA community

**This document describes the ideal future state. Current implementations are interim solutions until this architecture becomes feasible.**
