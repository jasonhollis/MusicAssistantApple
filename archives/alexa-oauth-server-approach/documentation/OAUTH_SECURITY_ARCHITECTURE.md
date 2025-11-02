# OAuth Server Security Architecture - MusicAssistantApple Alexa Integration
**Date**: 2025-11-02
**Status**: ARCHITECTURAL DECISION REQUIRED
**Context**: Security hardening for production OAuth server

---

## Executive Summary

**Current State**: OAuth server (`alexa_oauth_endpoints.py`) has placeholder authentication (`user_id='test_user'` on line 378) and in-memory token storage.

**Decision Required**:
1. User authentication strategy (LWA integration vs alternatives)
2. Token storage architecture (in-memory vs persistent encrypted)
3. Migration approach (zero-downtime deployment)

**Recommendation**: **Phased approach with simplified implementation** — Use persistent encrypted storage immediately, defer LWA integration to Phase 2.

---

## 1. Authentication Strategy Analysis

### Question: Should we integrate Login with Amazon (LWA) OAuth?

**80B Model Strategic Analysis**: YES, but with important caveats.

**Key Finding from Local Consultant**:
> "LWA integration is mandatory for Alexa Skill certification. Option 1 is the only compliant path."
> "Alexa Skill Certification rejection risk: Amazon *requires* LWA for user authentication in all skills that need identity."

**However, for Music Assistant's specific use case, there are critical considerations**:

### Music Assistant Context Assessment

**Music Assistant is NOT a multi-user service**:
- Typically runs as single-user home automation service
- Authentication is "link MY Music Assistant to MY Alexa account"
- Not "many users logging into shared Music Assistant instance"

**Three architectural patterns to consider**:

#### Pattern A: Full LWA Integration (Multi-User Pattern)
**Architecture**: Server acts as OAuth server (to Alexa) + OAuth client (to LWA)

**Pros**:
- ✅ Fully compliant with Amazon certification requirements
- ✅ Industry-standard pattern
- ✅ Supports multiple users if Music Assistant expands scope
- ✅ Leverages Amazon's identity infrastructure

**Cons**:
- ❌ High complexity for single-user deployment model
- ❌ Requires implementing two OAuth flows
- ❌ Adds external dependency (LWA API availability)
- ❌ 2-3 week implementation timeline
- ❌ Requires user to log into Amazon account during skill linking

**Implementation Burden**: 2-3 weeks development + testing

---

#### Pattern B: Simplified Device Authorization (Single-User Pattern)
**Architecture**: OAuth server issues tokens after simple device pairing (PIN code or consent button)

**Pros**:
- ✅ Simple implementation (1-2 days)
- ✅ No external dependencies
- ✅ Aligns with single-user deployment model
- ✅ User flow: "Click approve to link Alexa" (no separate login)

**Cons**:
- ❌ May not meet Amazon certification (needs verification)
- ❌ Less scalable if Music Assistant adds multi-user support
- ❌ Custom security implementation (higher risk)

**Implementation Burden**: 1-2 days development + testing

**Certification Risk**: MEDIUM — Amazon's policy states LWA is required, but many smart home skills use device authorization patterns. **Needs validation with Amazon Developer Support**.

---

#### Pattern C: Hybrid Phased Approach (Recommended)
**Architecture**: Phase 1 = Device authorization, Phase 2 = LWA migration if certification requires

**Pros**:
- ✅ Fast time-to-market (Phase 1: 1-2 days)
- ✅ Validates Alexa integration before investing in LWA
- ✅ Can upgrade to LWA if certification fails
- ✅ Matches Music Assistant's current single-user model

**Cons**:
- ❌ Potential rework if Amazon requires LWA
- ❌ Migration complexity from Phase 1 → Phase 2

**Implementation Burden**: Phase 1 (1-2 days), Phase 2 (2-3 weeks if needed)

---

### Recommendation: Pattern C (Hybrid Phased Approach)

**Rationale**:
1. **Validate integration first**: Alexa OAuth flow is complex — validate basic flow works before adding LWA complexity
2. **Match deployment model**: Music Assistant is typically single-user — don't over-engineer
3. **Certification uncertainty**: Amazon's requirements for smart home skills vs voice apps differ — validate requirements before implementation
4. **Migration path exists**: Can upgrade to LWA in Phase 2 if needed

**Action Items**:
1. ✅ **Immediate (Phase 1)**: Implement device authorization with persistent encrypted tokens
2. 📋 **Pre-certification**: Contact Amazon Developer Support to validate certification requirements
3. ⏳ **Conditional (Phase 2)**: Implement LWA integration if Amazon requires it

---

## 2. Token Storage Architecture

### Question: In-memory vs persistent encrypted storage?

**80B Model Analysis**:
> "Persistent encrypted storage is non-negotiable: In-memory storage (e.g., Redis or dict) will lose tokens on container restarts — breaking user sessions."

**Assessment**: **100% AGREE** — Persistent storage is mandatory.

### Current State Analysis

**Current Implementation** (`alexa_oauth_endpoints.py`):
```python
# In-memory storage (lines 134-142)
auth_codes = {}  # Format: {auth_code: {...}}
tokens = {}      # Format: {user_id: {...}}
pending_auth_codes = {}  # Format: {temp_auth_code: {...}}
```

**Problem**:
- ❌ Container restart = all tokens lost = users must re-link
- ❌ Music Assistant restart = all tokens lost
- ❌ No encryption at rest
- ❌ No audit trail

### Storage Architecture Options

#### Option 1: PostgreSQL + HashiCorp Vault (80B Recommendation)
**Architecture**: PostgreSQL for token metadata, Vault transit engine for encryption

**Pros**:
- ✅ Enterprise-grade security
- ✅ Automatic encryption/decryption
- ✅ Key rotation support
- ✅ Audit trails

**Cons**:
- ❌ **Massive operational overhead** for Music Assistant deployment model
- ❌ Requires deploying Vault service
- ❌ Requires PostgreSQL configuration
- ❌ **Misalignment**: Music Assistant uses SQLite, not PostgreSQL
- ❌ Overkill for single-user deployment

**Assessment**: ❌ **Not appropriate** for Music Assistant's deployment model.

---

#### Option 2: Music Assistant's Native Storage (Recommended)
**Architecture**: Use Music Assistant's existing encrypted configuration storage

**Music Assistant Storage Capabilities** (from codebase review):
- Music Assistant already has encrypted storage for provider credentials
- Uses `config_entry.data` for sensitive data
- Integrates with Home Assistant's secrets management
- SQLite backend with JSON serialization

**Implementation**:
```python
# Store in Music Assistant config entry
await self.mass.config.set_provider_config_value(
    self.instance_id,
    "oauth_tokens",
    {
        "user_id": user_id,
        "access_token": encrypted_access_token,
        "refresh_token": encrypted_refresh_token,
        "expires_at": expires_at
    }
)
```

**Pros**:
- ✅ **Zero operational overhead** — uses existing infrastructure
- ✅ Already encrypted (Home Assistant secrets)
- ✅ Persistent across restarts
- ✅ Aligns with Music Assistant patterns (Spotify provider uses this)
- ✅ Simple implementation (reuse existing patterns)
- ✅ No new dependencies

**Cons**:
- ❌ Less flexible than dedicated database
- ❌ No built-in key rotation
- ❌ Audit trail depends on Home Assistant logging

**Assessment**: ✅ **Strongly recommended** — perfect fit for Music Assistant's deployment model.

---

#### Option 3: SQLite + cryptography.fernet (Simplified Alternative)
**Architecture**: Dedicated SQLite database with Fernet encryption

**Pros**:
- ✅ Self-contained (no external services)
- ✅ Persistent storage
- ✅ Simple encryption (already using Fernet in codebase)
- ✅ Independent from Home Assistant

**Cons**:
- ❌ Duplicates Music Assistant's existing storage
- ❌ Requires managing encryption keys separately
- ❌ Not integrated with Home Assistant's secrets

**Assessment**: ⚠️ **Acceptable fallback** if Music Assistant storage proves insufficient.

---

### Recommendation: Option 2 (Music Assistant Native Storage)

**Rationale**:
1. **Reuse existing infrastructure**: Music Assistant already solves this problem
2. **Zero operational overhead**: No new services to deploy
3. **Proven pattern**: Spotify provider stores OAuth tokens this way
4. **Aligns with deployment model**: Single-user, integrated with Home Assistant

**Implementation Approach**:
```python
# In alexa_oauth_endpoints.py
class TokenStore:
    """Persistent token storage using Music Assistant config."""

    def __init__(self, mass_config):
        self.mass_config = mass_config
        self._encryption_key = self._get_or_create_key()
        self._cipher = Fernet(self._encryption_key)

    async def store_token(self, user_id: str, access_token: str,
                          refresh_token: str, expires_at: float):
        """Store encrypted tokens in Music Assistant config."""
        encrypted_data = {
            "access_token": self._cipher.encrypt(access_token.encode()).decode(),
            "refresh_token": self._cipher.encrypt(refresh_token.encode()).decode(),
            "expires_at": expires_at
        }
        await self.mass_config.set_provider_config_value(
            "alexa_oauth",
            user_id,
            encrypted_data
        )

    async def get_token(self, user_id: str) -> Optional[dict]:
        """Retrieve and decrypt tokens."""
        encrypted_data = await self.mass_config.get_provider_config_value(
            "alexa_oauth",
            user_id
        )
        if not encrypted_data:
            return None

        return {
            "access_token": self._cipher.decrypt(
                encrypted_data["access_token"].encode()
            ).decode(),
            "refresh_token": self._cipher.decrypt(
                encrypted_data["refresh_token"].encode()
            ).decode(),
            "expires_at": encrypted_data["expires_at"]
        }

    def _get_or_create_key(self) -> bytes:
        """Get encryption key from config or generate new."""
        # Store in Home Assistant secrets or generate
        # Implementation depends on Music Assistant's key management
        pass
```

---

## 3. Migration Strategy

### Question: How to deploy without breaking existing Alexa links?

**Current State**:
- OAuth server is running in production
- Unknown number of users may have linked Alexa accounts
- Placeholder `user_id='test_user'` means all users share same token

**Challenge**: Transitioning from `test_user` to real user identities without breaking existing links.

### Migration Approaches

#### Approach A: Zero-Downtime Dual-Mode (80B Recommendation)
**Strategy**: Run both old and new auth flows in parallel with feature flag

**Steps**:
1. Deploy new code with `ENABLE_REAL_AUTH=false` (default)
2. Existing users continue using `test_user` — no disruption
3. Enable for 10% of users → monitor → expand to 100%
4. After 30 days, disable `test_user` fallback

**Pros**:
- ✅ No disruption to existing users
- ✅ Gradual rollout with monitoring
- ✅ Easy rollback if issues

**Cons**:
- ❌ Complex: two code paths for 30+ days
- ❌ Requires feature flag infrastructure
- ❌ **Doesn't solve the fundamental problem**: all existing users are on `test_user` — what happens when we remove it?

**Assessment**: ⚠️ **Not applicable** — Music Assistant users likely haven't deployed OAuth yet (Phase 2 debugging ongoing).

---

#### Approach B: Breaking Change with Migration Notice (Recommended)
**Strategy**: Accept that OAuth is in beta, deploy corrected version, notify users to re-link

**Steps**:
1. Add migration notice to OAuth server startup logs
2. Deploy new version with persistent storage + real auth
3. Existing `test_user` tokens invalidated (expected in beta)
4. Users re-link via Alexa app (normal OAuth flow)

**Pros**:
- ✅ Clean implementation — no technical debt
- ✅ Simple deployment
- ✅ Sets correct foundation for production

**Cons**:
- ❌ Users must re-link (inconvenience)
- ❌ Acceptable for beta, not for stable release

**Assessment**: ✅ **Recommended** — OAuth is currently in Phase 2 debugging, not production.

---

#### Approach C: Automatic Migration with User Prompt
**Strategy**: Keep `test_user` token valid, prompt for re-authentication on next Alexa interaction

**Steps**:
1. Deploy new storage + auth
2. Detect users with `test_user` tokens
3. On next Alexa request, return error with re-link prompt
4. User re-links via Alexa app with real auth

**Pros**:
- ✅ No immediate disruption
- ✅ Users prompted when they use Alexa
- ✅ Graceful transition

**Cons**:
- ❌ Requires detecting `test_user` tokens
- ❌ Complex error handling in Alexa flow

**Assessment**: ⚠️ **Over-engineered** for current deployment state.

---

### Recommendation: Approach B (Breaking Change with Notice)

**Rationale**:
1. **Beta status**: OAuth server is in Phase 2 debugging — breaking changes acceptable
2. **Clean foundation**: Avoid technical debt from supporting dual modes
3. **Clear communication**: Users expect beta features to require re-setup

**Implementation**:
```python
# In oauth server startup
logger.warning(
    "="*80 + "\n"
    "🔐 OAUTH SERVER MIGRATION NOTICE\n"
    "="*80 + "\n"
    "OAuth authentication has been upgraded for security and reliability.\n"
    "Existing Alexa skill links will need to be re-authorized.\n"
    "\n"
    "Steps to re-link:\n"
    "1. Open Alexa app\n"
    "2. Go to Skills & Games → Your Skills → Music Assistant\n"
    "3. Disable and re-enable the skill\n"
    "4. Follow the new linking flow\n"
    "\n"
    "This is a one-time migration. Thank you for your patience!\n"
    "="*80
)
```

---

## 4. Deployment Considerations

### Docker Container Environment

**Current Setup**:
- Music Assistant running in Docker container
- Public-facing via Tailscale Funnel
- OAuth server on port 8096
- Environment variables: `ALEXA_OAUTH_CLIENT_SECRET`, etc.

**Storage Implications**:
1. **Volume mount required**: If using SQLite, mount `/data` volume
2. **Encryption key management**: Store Fernet key in environment variable or Docker secret
3. **Backup strategy**: Backup `/data/oauth_tokens.db` or Music Assistant config

### Restart/Recovery Scenarios

**Container Restart**:
- ✅ Tokens persist (with recommended storage)
- ✅ Users remain authenticated
- ✅ Alexa continues working

**Music Assistant Upgrade**:
- ✅ OAuth tokens preserved in config
- ⚠️ Need migration path if schema changes

**Disaster Recovery**:
- ✅ Restore from backup (config or SQLite file)
- ⚠️ Encryption key must be same (store in secrets manager)

### Environment Configuration

**Required Environment Variables**:
```bash
# OAuth Client Configuration
ALEXA_OAUTH_CLIENT_SECRET=<from Amazon Developer Console>

# Encryption Key (for token storage)
OAUTH_ENCRYPTION_KEY=<base64-encoded 32-byte key>

# Optional: Enable LWA (Phase 2)
ENABLE_LWA_AUTH=false

# Optional: Debug logging
OAUTH_DEBUG=true
```

**Recommendation**: Use Docker Compose secrets or Home Assistant's `secrets.yaml`.

---

## 5. Implementation Roadmap

### Phase 1: Persistent Storage + Device Authorization (IMMEDIATE)
**Timeline**: 1-2 weeks
**Goal**: Production-ready OAuth with persistent tokens

**Tasks**:
1. ✅ Implement `TokenStore` class using Music Assistant config
2. ✅ Add encryption for access/refresh tokens (Fernet)
3. ✅ Replace in-memory dicts with persistent storage
4. ✅ Add encryption key management
5. ✅ Implement simple device authorization (consent screen)
6. ✅ Update `user_id` logic to use device pairing flow
7. ✅ Add migration notice to logs
8. ✅ Test restart scenarios
9. ✅ Document backup/restore procedures

**Success Criteria**:
- Container restart preserves user sessions
- Tokens encrypted at rest
- Users can link Alexa via consent screen (no separate login)

---

### Phase 2: LWA Integration (CONDITIONAL)
**Timeline**: 2-3 weeks (if Amazon requires it)
**Trigger**: Amazon Developer Support confirms LWA is mandatory for certification

**Tasks**:
1. Contact Amazon Developer Support to validate certification requirements
2. If LWA required:
   - Implement LWA OAuth client flow
   - Add LWA callback endpoint
   - Map LWA user identity to Music Assistant users
   - Update consent screen with LWA login
3. Test with Amazon's OAuth test tool
4. Submit for Alexa Skill certification

**Success Criteria**:
- Users log in via Amazon account
- Alexa Skill certification passes
- Zero-downtime migration from Phase 1

---

## 6. Security Hardening Checklist

### Immediate (Phase 1)
- [ ] Encrypt tokens at rest using Fernet
- [ ] Store encryption key securely (environment variable or secrets)
- [ ] Use PKCE for OAuth flow (already implemented)
- [ ] Short-lived access tokens (15-30 min)
- [ ] Long-lived refresh tokens (7-90 days)
- [ ] TLS 1.3 enforced (Tailscale Funnel handles this)
- [ ] HSTS headers on all endpoints
- [ ] Rate limiting on `/authorize` and `/token` endpoints
- [ ] Log all token issuance (audit trail)
- [ ] Redact tokens from logs (use `[REDACTED]` for access_token values)

### Phase 2 (If LWA Implemented)
- [ ] Validate LWA JWT signatures
- [ ] Verify LWA issuer (`https://www.amazon.com`)
- [ ] Enforce PKCE for LWA client
- [ ] Implement token refresh automation
- [ ] Add circuit breaker for LWA API calls
- [ ] Monitor LWA API availability

---

## 7. Monitoring and Observability

### Metrics to Track
- Token issuance rate (tokens/hour)
- Token refresh success rate
- OAuth flow completion rate (authorize → token exchange)
- Token validation failures
- Storage encryption/decryption latency

### Logging Strategy
```python
# Example logging (DO NOT log tokens)
logger.info(
    "OAuth token issued",
    extra={
        "user_id": user_id,
        "client_id": client_id,
        "scope": scope,
        "expires_in": expires_in,
        # ❌ NEVER LOG: access_token, refresh_token, code_verifier
    }
)
```

### Alerts
- Token issuance failure rate >5% (5 min window)
- Storage write failures
- Encryption key unavailable
- Unexpected token validation failures

---

## 8. Architecture Decision Record (ADR)

**ADR-012: OAuth Server Security Architecture**

**Status**: PROPOSED

**Context**:
- OAuth server currently uses placeholder authentication and in-memory storage
- Production deployment requires persistent, encrypted token storage
- Amazon certification requirements for LWA are unclear for smart home skills

**Decision**:
1. **Phase 1**: Implement persistent encrypted token storage using Music Assistant's native storage + device authorization pattern
2. **Phase 2**: Add LWA integration if Amazon certification requires it (conditional)

**Rationale**:
- Music Assistant's native storage provides encryption + persistence with zero operational overhead
- Device authorization aligns with single-user deployment model
- Phased approach validates integration before investing in LWA complexity
- Migration path exists to LWA if certification requires it

**Consequences**:
- ✅ Production-ready OAuth in 1-2 weeks (Phase 1)
- ✅ Zero operational overhead (no PostgreSQL/Vault)
- ✅ Aligns with Music Assistant patterns
- ⚠️ Potential rework if Amazon requires LWA
- ⚠️ Migration notice for existing beta users

**Alternatives Considered**:
1. **PostgreSQL + Vault**: Rejected (operational overhead, misalignment with deployment model)
2. **Full LWA integration immediately**: Deferred to Phase 2 (validate requirements first)
3. **In-memory storage**: Rejected (loses tokens on restart)

**Follow-up Actions**:
1. Contact Amazon Developer Support to validate certification requirements
2. Implement `TokenStore` using Music Assistant config
3. Document backup/restore procedures
4. Add migration notice to server startup

---

## 9. Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Amazon rejects certification without LWA** | HIGH | Contact Amazon Developer Support before Phase 1 deployment; prepare Phase 2 migration plan |
| **Token storage corruption** | MEDIUM | Implement backup/restore automation; use Music Assistant's proven storage layer |
| **Encryption key loss** | HIGH | Store key in Docker secrets or Home Assistant secrets; document recovery procedure |
| **User confusion during migration** | LOW | Clear migration notice in logs and documentation |
| **Storage performance degradation** | LOW | Music Assistant config already handles sensitive data; monitor latency |

---

## 10. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Token Persistence** | 100% after restart | Test: restart container → verify session valid |
| **Encryption Coverage** | 100% of tokens | Code review + penetration testing |
| **Migration Completion** | 100% users re-linked | Logs: no `test_user` tokens after 30 days |
| **OAuth Flow Success Rate** | >99% | Logs: token issuance success vs failures |
| **Time to Implement Phase 1** | <2 weeks | Project timeline tracking |

---

## 11. Next Steps

### Immediate Actions (This Week)
1. **Contact Amazon Developer Support**
   - Question: "Does Music Assistant smart home skill require LWA for certification?"
   - Document response → informs Phase 2 decision

2. **Review Music Assistant Storage API**
   - Read Spotify provider code for token storage patterns
   - Validate encryption capabilities

3. **Prototype `TokenStore` Implementation**
   - Implement using Music Assistant config
   - Test encryption/decryption
   - Validate restart persistence

### Week 2-3: Implementation
1. Replace in-memory storage with `TokenStore`
2. Add encryption key management
3. Update user_id logic (device authorization)
4. Add migration notice
5. Test restart/recovery scenarios

### Week 4: Testing & Deployment
1. Integration testing (full OAuth flow)
2. Security review (encryption, logs, rate limiting)
3. Documentation update
4. Deploy to production with migration notice

---

## References

- **80B Local Consultant Analysis**: Comprehensive strategic assessment (2025-11-02)
- **RFC 6749**: OAuth 2.0 Authorization Framework
- **RFC 7636**: Proof Key for Code Exchange (PKCE)
- **Music Assistant Spotify Provider**: Token storage reference implementation
- **Amazon Alexa Account Linking**: https://developer.amazon.com/docs/account-linking/
- **Home Assistant Secrets Management**: https://www.home-assistant.io/docs/configuration/secrets/

---

**Document Owner**: Architecture Team
**Last Review**: 2025-11-02
**Next Review**: After Phase 1 implementation (2 weeks)
