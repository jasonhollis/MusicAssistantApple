# OAuth 2.0 Documentation Index
**Purpose**: Navigation guide for complete OAuth implementation documentation
**Last Updated**: 2025-10-27
**Status**: Complete - All layers documented

## Overview

This documentation covers the complete OAuth 2.0 implementation for Music Assistant Alexa integration, following Clean Architecture principles with strict dependency rules.

## Documentation Layers (00-05)

### Layer 00: ARCHITECTURE (Innermost - Most Stable)
**Purpose**: Core principles independent of technology

**[OAUTH_PRINCIPLES.md](00_ARCHITECTURE/OAUTH_PRINCIPLES.md)**
- OAuth 2.0 fundamental concepts
- Authorization vs authentication
- Client security models (public vs confidential)
- PKCE cryptographic security
- Token lifecycle and flow principles
- **Technology-agnostic** - no implementation details

**Key Concepts**:
- Separation of authorization and authentication
- Token-based access control
- PKCE for public clients (voice assistants, mobile apps)
- Time-limited access with renewal
- Scope-based permissions

---

### Layer 01: USE_CASES (Business Logic)
**Purpose**: User workflows and actor goals

**[ALEXA_ACCOUNT_LINKING.md](01_USE_CASES/ALEXA_ACCOUNT_LINKING.md)**
- Complete account linking workflow
- User perspective (approval flow)
- Alexa perspective (authorization request)
- Success and failure scenarios
- Alternative flows (denial, expiration, network failures)
- Business rules (BR-1 through BR-6)

**Workflows Documented**:
- Main: Link Alexa to Music Assistant (8 steps)
- Alternative: User denies authorization
- Alternative: Authorization code expires
- Alternative: Network failure
- Use Case: Refresh access token
- Use Case: Revoke Alexa access

---

### Layer 02: REFERENCE (Quick Lookup)
**Purpose**: Constants, formats, and quick reference

**[OAUTH_CONSTANTS.md](02_REFERENCE/OAUTH_CONSTANTS.md)**
- Token lifetimes and expirations
- Token format specifications (base64url, lengths)
- PKCE parameters and computation
- Scope definitions
- Error codes and meanings
- Client configuration reference
- Real-world examples from production

**Quick Reference Tables**:
- Token lifetimes: Auth code (5 min), Access token (1 hr), Refresh token (90 days)
- Token formats: 43 characters URL-safe base64
- Error codes: invalid_grant, invalid_client, invalid_request, etc.
- PKCE: code_verifier (43-128 chars), code_challenge (SHA-256 → 43 chars)

---

### Layer 03: INTERFACES (Contracts)
**Purpose**: Stable API contracts

**[OAUTH_ENDPOINTS.md](03_INTERFACES/OAUTH_ENDPOINTS.md)**
- Authorization endpoint: GET /alexa/authorize
- Consent approval: POST /alexa/approve
- Token endpoint: POST /alexa/token
- Request/response formats
- Error responses
- HTTP Basic Authentication
- Versioning policy

**Endpoint Contracts**:
- **Authorization**: Query params → HTML consent screen OR 302 redirect
- **Approval**: Form data → 302 redirect with final code
- **Token**: POST body → JSON token response
- **Health**: GET /health → JSON status

**Guarantees**:
- Backward compatibility for all required parameters
- Forward compatibility for optional parameters
- 90-day deprecation notice policy

---

### Layer 04: INFRASTRUCTURE (Implementation)
**Purpose**: Technology choices and deployment

**[OAUTH_IMPLEMENTATION.md](04_INFRASTRUCTURE/OAUTH_IMPLEMENTATION.md)**
- Technology stack (Python 3.11+, aiohttp, cryptography)
- File structure (/data/alexa_oauth_endpoints.py)
- Current deployment: Standalone server (port 8096)
- Recommended deployment: Integrated with Music Assistant (port 8095)
- Implementation details (PKCE, client validation, token storage)
- Configuration management (oauth_clients.json)
- Security measures (implemented and planned)

**Key Files**:
- `/data/alexa_oauth_endpoints.py` - 874 lines OAuth implementation
- `/data/start_oauth_server.py` - Server startup script
- `/data/oauth_clients.json` - Client configuration
- `/data/oauth_debug.log` - Request/response logging

**Deployment Architectures**:
- **Current**: Standalone Python process on port 8096
- **Recommended**: Integration with Music Assistant webserver (port 8095)

---

### Layer 05: OPERATIONS (Outermost - Most Volatile)
**Purpose**: Operational procedures and troubleshooting

**[OAUTH_TROUBLESHOOTING.md](05_OPERATIONS/OAUTH_TROUBLESHOOTING.md)**
- Quick diagnostic commands
- 7 common issues with step-by-step solutions
- Emergency procedures
- Monitoring and alerting
- Validation checklist

**Common Issues Covered**:
1. Server crashes on startup
2. 502 Bad Gateway from reverse proxy
3. redirect_uri mismatch
4. PKCE verification failed
5. Authorization code expired
6. Client validation failed
7. Generic "Unable to link the skill" error

---

## Documentation Dependency Rules

**Clean Architecture Principle**: Documentation layers only reference inner/same layers, never outer layers.

```
Layer 00 (Architecture)     → References: None (innermost)
Layer 01 (Use Cases)        → References: Layer 00
Layer 02 (Reference)        → References: Layer 00, 01
Layer 03 (Interfaces)       → References: Layer 00, 01, 02
Layer 04 (Infrastructure)   → References: Layer 00, 01, 02, 03
Layer 05 (Operations)       → References: Layer 00, 01, 02, 03, 04
```

**Why This Matters**:
- Architecture principles remain technology-agnostic
- Use cases don't depend on implementation details
- Interfaces can change implementation without breaking contracts
- Operations can reference everything (most volatile layer)

---

## Quick Navigation by Role

### For Architects
**Start here**:
1. [OAUTH_PRINCIPLES.md](00_ARCHITECTURE/OAUTH_PRINCIPLES.md) - Core principles
2. [OAUTH_ENDPOINTS.md](03_INTERFACES/OAUTH_ENDPOINTS.md) - API contracts
3. [OAUTH_IMPLEMENTATION.md](04_INFRASTRUCTURE/OAUTH_IMPLEMENTATION.md) - Technology choices

**Focus on**:
- Security properties and guarantees
- Architectural constraints
- Design rationale
- Quality attributes (security, scalability, performance)

### For Developers
**Start here**:
1. [OAUTH_IMPLEMENTATION.md](04_INFRASTRUCTURE/OAUTH_IMPLEMENTATION.md) - How it's built
2. [OAUTH_ENDPOINTS.md](03_INTERFACES/OAUTH_ENDPOINTS.md) - API specs
3. [OAUTH_CONSTANTS.md](02_REFERENCE/OAUTH_CONSTANTS.md) - Quick reference

**Focus on**:
- Implementation details and code examples
- PKCE validation logic
- Token generation and storage
- Integration with Music Assistant

### For DevOps/Operations
**Start here**:
1. [OAUTH_TROUBLESHOOTING.md](05_OPERATIONS/OAUTH_TROUBLESHOOTING.md) - Solve problems
2. [OAUTH_IMPLEMENTATION.md](04_INFRASTRUCTURE/OAUTH_IMPLEMENTATION.md) - Deployment
3. [OAUTH_ENDPOINTS.md](03_INTERFACES/OAUTH_ENDPOINTS.md) - Test endpoints

**Focus on**:
- Diagnostic commands
- Common issues and solutions
- Health check monitoring
- Emergency procedures
- Log file locations

### For Product Managers
**Start here**:
1. [ALEXA_ACCOUNT_LINKING.md](01_USE_CASES/ALEXA_ACCOUNT_LINKING.md) - User workflows
2. [OAUTH_PRINCIPLES.md](00_ARCHITECTURE/OAUTH_PRINCIPLES.md) - Why OAuth?
3. [OAUTH_CONSTANTS.md](02_REFERENCE/OAUTH_CONSTANTS.md) - Token lifetimes

**Focus on**:
- User experience (consent screen, approval flow)
- Success criteria
- Business rules
- Security guarantees for users

### For Security Auditors
**Start here**:
1. [OAUTH_PRINCIPLES.md](00_ARCHITECTURE/OAUTH_PRINCIPLES.md) - Security model
2. [OAUTH_ENDPOINTS.md](03_INTERFACES/OAUTH_ENDPOINTS.md) - Attack surface
3. [OAUTH_IMPLEMENTATION.md](04_INFRASTRUCTURE/OAUTH_IMPLEMENTATION.md) - Security measures

**Focus on**:
- PKCE implementation (prevents code interception)
- State parameter (CSRF protection)
- Token entropy and randomness
- Authorization code single-use validation
- Redirect URI exact matching

---

## Current Implementation Status

### What's Working ✅
- Authorization endpoint serving consent screens
- Token endpoint exchanging codes for tokens
- PKCE validation for public clients (Alexa)
- Real Alexa requests captured and logged
- OAuth server deployed on port 8096
- Reverse proxy routing (https://dev.jasonhollis.com/alexa/*)

### Known Limitations ⚠️
- **In-memory token storage** (lost on restart)
- **Mock user authentication** (uses "test_user")
- **Standalone server** (not integrated with Music Assistant)
- **No token revocation API**
- **No rate limiting**

### Recommended Next Steps
1. **Integrate with Music Assistant webserver** (port 8095)
   - Better HA OS lifecycle management
   - Auto-restart on failure
   - Unified logging
2. **Implement real user authentication**
   - Link OAuth user_id to Music Assistant accounts
   - Require passkey or Login with Amazon
3. **Persist tokens to database**
   - Survive server restarts
   - Support multiple concurrent sessions
4. **Add token validation to Music Assistant API**
   - Protect endpoints with OAuth tokens
   - Validate scope before granting access

---

## Real-World Data Captured

### Successful Authorization Flow (Oct 26, 2025)

**Timeline**:
- **20:11:26 UTC**: User's iPhone (Australia) requests authorization
  - Client: Amazon Alexa iOS 18.7
  - Redirect URI: https://alexa.amazon.co.jp/api/skill/link/MKXZK47785HJ2
  - State: (CSRF token)
  - Scope: music.control user:read

- **20:11:26 UTC**: OAuth server serves consent screen
  - HTML form with permissions list
  - "Approve & Link Account" button

- **20:11:27 UTC**: User approves authorization
  - Authorization code generated (43 chars, 256 bits entropy)
  - Redirect to Alexa with code + state

- **20:11:29 UTC**: Amazon servers exchange code for tokens
  - Source IP: 54.240.230.242 (AWS Tokyo)
  - grant_type: authorization_code
  - code_verifier: (PKCE proof)
  - Response: access_token, refresh_token, expires_in: 3600

**Total Flow Time**: 3 seconds (mostly user interaction)

---

## Verification Checklist

### Documentation Completeness
- [x] Layer 00: Architecture principles documented
- [x] Layer 01: User workflows documented
- [x] Layer 02: Reference data documented
- [x] Layer 03: API contracts documented
- [x] Layer 04: Implementation documented
- [x] Layer 05: Operations procedures documented
- [x] Dependency rule compliance verified
- [x] Real-world examples included
- [x] Troubleshooting guide complete

### Technical Implementation
- [x] OAuth 2.0 RFC 6749 compliant
- [x] PKCE RFC 7636 compliant
- [x] Authorization endpoint implemented
- [x] Token endpoint implemented
- [x] PKCE validation working
- [x] Client validation working
- [x] Error handling implemented
- [x] Debug logging enabled
- [x] Real Alexa requests tested

### Deployment Readiness
- [x] Server deployed and running
- [x] Reverse proxy configured
- [x] HTTPS enabled (Let's Encrypt)
- [x] Health check endpoint working
- [x] Logs accessible and monitored
- [ ] Integration with Music Assistant (recommended)
- [ ] Production user authentication (planned)
- [ ] Token persistence (planned)

---

## Related Documentation

### Project-Level Documentation
- **[OAUTH_IMPLEMENTATION_STATUS.md](../OAUTH_IMPLEMENTATION_STATUS.md)** - Current deployment status
- **[PHASE_2_FINDINGS.md](../PHASE_2_FINDINGS.md)** - Testing results and analysis
- **[ALEXA_OAUTH_INTEGRATION_PROPER.md](../ALEXA_OAUTH_INTEGRATION_PROPER.md)** - Integration strategy

### External References
- **RFC 6749**: OAuth 2.0 Authorization Framework
  - https://datatracker.ietf.org/doc/html/rfc6749
- **RFC 7636**: Proof Key for Code Exchange (PKCE)
  - https://datatracker.ietf.org/doc/html/rfc7636
- **RFC 6750**: Bearer Token Usage
  - https://datatracker.ietf.org/doc/html/rfc6750
- **OAuth 2.0 Security Best Current Practice**
  - https://datatracker.ietf.org/doc/html/draft-ietf-oauth-security-topics

---

## Document History

| Date | Layer | Document | Change |
|------|-------|----------|--------|
| 2025-10-27 | 00 | OAUTH_PRINCIPLES.md | Created - Architecture principles |
| 2025-10-27 | 01 | ALEXA_ACCOUNT_LINKING.md | Created - User workflows |
| 2025-10-27 | 02 | OAUTH_CONSTANTS.md | Created - Reference data |
| 2025-10-27 | 03 | OAUTH_ENDPOINTS.md | Created - API contracts |
| 2025-10-27 | 04 | OAUTH_IMPLEMENTATION.md | Created - Implementation guide |
| 2025-10-27 | 05 | OAUTH_TROUBLESHOOTING.md | Created - Operations guide |
| 2025-10-27 | -- | OAUTH_DOCUMENTATION_INDEX.md | Created - This index |

---

## Feedback and Maintenance

### Documentation Quality Standards
- **Testability**: Can readers verify documentation matches reality?
- **Dependency Rule**: Does each layer only reference inner layers?
- **Intent Clarity**: Can readers understand purpose in 30 seconds?
- **Completeness**: Are all aspects of OAuth implementation covered?
- **Accuracy**: Does documentation match deployed implementation?

### Maintenance Schedule
- **Weekly**: Review OAUTH_TROUBLESHOOTING.md for new issues
- **Monthly**: Update OAUTH_IMPLEMENTATION.md with deployment changes
- **Per Release**: Update OAUTH_ENDPOINTS.md if contracts change
- **Annually**: Review OAUTH_PRINCIPLES.md for continued relevance

### Contributing Changes
When updating documentation:
1. **Maintain layer separation** - Don't break dependency rule
2. **Update related documents** - Keep consistency across layers
3. **Test examples** - Verify code snippets work
4. **Update this index** - Record changes in Document History
5. **Verify principles** - Ensure changes align with Clean Architecture

---

**This documentation provides complete coverage of the OAuth 2.0 implementation for Music Assistant Alexa integration, from abstract principles to concrete operational procedures.**
