# OAuth Security Architecture - Executive Summary
**Date**: 2025-11-02
**Decision**: PHASED IMPLEMENTATION RECOMMENDED

---

## TL;DR (30 seconds)

**Current Problem**: OAuth server has placeholder `user_id='test_user'` and loses tokens on restart.

**Recommended Solution**: **Two-phase approach**
- **Phase 1 (Now)**: Persistent encrypted storage + simple device authorization (1-2 weeks)
- **Phase 2 (Conditional)**: Login with Amazon (LWA) integration if Amazon requires it (2-3 weeks)

**Why Phased?**: Validate OAuth integration works before investing in LWA complexity. Music Assistant is single-user — LWA may be overkill.

---

## Three Key Decisions

### 1. User Authentication Strategy

**Question**: Should we integrate Login with Amazon (LWA)?

**Answer**: **YES, but in Phase 2** (conditional on Amazon certification requirements)

| Approach | Timeline | Pros | Cons | Recommendation |
|----------|----------|------|------|----------------|
| **Full LWA Now** | 2-3 weeks | Amazon certified, scalable | Complex, external dependency | ❌ Defer |
| **Device Auth Now** | 1-2 weeks | Simple, aligns with single-user model | May need LWA later | ✅ Phase 1 |
| **Phased Hybrid** | 1-2 weeks + 2-3 weeks | Validate first, upgrade if needed | Potential rework | ✅ **RECOMMENDED** |

**Rationale**:
- Music Assistant is single-user (not multi-user service)
- OAuth is in beta (Phase 2 debugging) — validate basic flow first
- Can upgrade to LWA if Amazon certification requires it
- **Action**: Contact Amazon Developer Support to validate requirements

---

### 2. Token Storage Architecture

**Question**: In-memory vs persistent encrypted storage?

**Answer**: **Persistent encrypted storage using Music Assistant's native config** (MANDATORY)

| Storage Option | Pros | Cons | Recommendation |
|----------------|------|------|----------------|
| **In-Memory** (current) | Simple | ❌ Loses tokens on restart | ❌ **NOT VIABLE** |
| **PostgreSQL + Vault** (80B rec) | Enterprise security | ❌ Massive overhead, misaligned | ❌ Overkill |
| **Music Assistant Config** | Zero overhead, proven, encrypted | Less flexible | ✅ **RECOMMENDED** |
| **SQLite + Fernet** | Self-contained | Duplicates MA storage | ⚠️ Fallback |

**Why Music Assistant Config?**
- ✅ Already encrypted (Home Assistant secrets)
- ✅ Persistent across restarts
- ✅ Zero operational overhead
- ✅ Proven pattern (Spotify provider uses this)
- ✅ Aligns with single-user deployment

**Implementation**: Use `TokenStore` class wrapping Music Assistant's config API with Fernet encryption.

---

### 3. Migration Strategy

**Question**: How to deploy without breaking existing Alexa links?

**Answer**: **Breaking change with migration notice** (acceptable for beta)

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **Zero-Downtime Dual Mode** | No disruption | Complex, doesn't solve test_user problem | ❌ Over-engineered |
| **Breaking Change + Notice** | Clean foundation | Users re-link (beta acceptable) | ✅ **RECOMMENDED** |
| **Auto-Migration** | Graceful | Complex error handling | ❌ Over-engineered |

**Rationale**:
- OAuth is currently in **Phase 2 debugging** (not production)
- Breaking changes acceptable for beta features
- Clean implementation avoids technical debt
- Users expect beta to require occasional re-setup

**Migration Notice**:
```
🔐 OAUTH SERVER MIGRATION NOTICE
OAuth authentication has been upgraded for security.
Existing Alexa links need re-authorization (one-time).

Steps: Alexa app → Skills → Music Assistant → Disable/Re-enable
```

---

## Implementation Roadmap

### Phase 1: Persistent Storage + Device Auth (1-2 weeks) ✅ IMMEDIATE

**Goal**: Production-ready OAuth with persistent tokens

**Tasks**:
1. Implement `TokenStore` using Music Assistant config
2. Encrypt tokens with Fernet
3. Replace in-memory dicts with persistent storage
4. Add device authorization (consent screen)
5. Test restart/recovery scenarios

**Success Criteria**:
- ✅ Container restart preserves user sessions
- ✅ Tokens encrypted at rest
- ✅ Simple user flow: "Click approve to link Alexa"

---

### Phase 2: LWA Integration (2-3 weeks) ⏳ CONDITIONAL

**Trigger**: Amazon Developer Support confirms LWA required for certification

**Tasks**:
1. Contact Amazon Developer Support (validate requirements)
2. If LWA required:
   - Implement LWA OAuth client
   - Add LWA callback endpoint
   - Map LWA user identity to Music Assistant
   - Update consent screen with Amazon login

**Success Criteria**:
- ✅ Users log in via Amazon account
- ✅ Alexa Skill certification passes

---

## Security Hardening (Phase 1)

**Mandatory Items**:
- [ ] Encrypt tokens at rest (Fernet)
- [ ] Store encryption key securely (Docker secrets or HA secrets)
- [ ] Short-lived access tokens (15-30 min)
- [ ] Long-lived refresh tokens (7-90 days)
- [ ] Rate limiting on OAuth endpoints
- [ ] Redact tokens from logs
- [ ] Log token issuance (audit trail)
- [ ] Test backup/restore procedures

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Amazon rejects cert without LWA** | HIGH | Contact Amazon Support before Phase 1; prepare Phase 2 plan |
| **Token corruption** | MEDIUM | Use Music Assistant's proven storage; implement backups |
| **Encryption key loss** | HIGH | Store in Docker/HA secrets; document recovery |
| **User confusion (migration)** | LOW | Clear migration notice in logs |

---

## Deployment Considerations

**Docker Environment**:
- Volume mount: `/data` (if using SQLite fallback)
- Environment vars: `OAUTH_ENCRYPTION_KEY`, `ALEXA_OAUTH_CLIENT_SECRET`
- Backup strategy: Music Assistant config or SQLite file

**Restart Scenarios**:
- ✅ Container restart → tokens persist
- ✅ Music Assistant upgrade → tokens preserved
- ⚠️ Disaster recovery → restore from backup (encryption key must match)

---

## Next Steps (This Week)

### Day 1-2: Validation
1. **Contact Amazon Developer Support**
   - Question: "Does Music Assistant smart home skill require LWA for certification?"
   - Document response → informs Phase 2 decision

2. **Review Music Assistant Codebase**
   - Read Spotify provider token storage code
   - Validate encryption capabilities

### Day 3-5: Prototype
1. Implement `TokenStore` class
2. Test encryption/decryption
3. Validate restart persistence

### Week 2-3: Implementation
- Replace in-memory storage
- Add encryption key management
- Implement device authorization
- Test restart scenarios

### Week 4: Deploy
- Integration testing
- Security review
- Deploy with migration notice

---

## Comparison: Local 80B Recommendation vs Final Decision

**80B Consultant Recommended**:
- ✅ LWA integration (mandatory for certification)
- ✅ PostgreSQL + HashiCorp Vault (enterprise security)
- ✅ Zero-downtime dual-mode migration

**Final Decision (Context-Adapted)**:
- ⏳ LWA integration **deferred to Phase 2** (validate requirements first)
- ✅ Music Assistant native storage (zero overhead, proven)
- ✅ Breaking change migration (acceptable for beta)

**Why the Difference?**
- **80B analysis assumed** multi-user enterprise deployment
- **Music Assistant reality**: Single-user home automation service
- **Pragmatic adjustment**: Match solution complexity to deployment model
- **Same security outcome**: Persistent encrypted tokens, just simpler infrastructure

**80B Strategic Insight That Guided Decision**:
> "LWA integration is mandatory for Alexa Skill certification."

This insight drove the **phased approach**: validate requirements before implementation, but be ready to implement LWA in Phase 2 if Amazon requires it.

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Token Persistence** | 100% after restart | Test: restart container → session valid |
| **Encryption Coverage** | 100% of tokens | Code review + pen testing |
| **OAuth Success Rate** | >99% | Logs: token issuance success rate |
| **Phase 1 Timeline** | <2 weeks | Project tracking |
| **User Migration** | 100% re-linked | No `test_user` tokens after 30 days |

---

## References

- **Full Analysis**: `OAUTH_SECURITY_ARCHITECTURE.md` (detailed architectural assessment)
- **80B Consultant**: Local strategic analysis (2025-11-02, 30.3 tok/s, 45.8 GB peak memory)
- **Current Code**: `alexa_oauth_endpoints.py` (placeholder on line 378)
- **Music Assistant Patterns**: Spotify provider token storage

---

**Recommendation**: **Proceed with Phase 1 implementation immediately**. Contact Amazon Developer Support in parallel to validate Phase 2 requirements.

**Estimated Timeline**:
- **Phase 1**: 1-2 weeks → Production-ready OAuth with persistent tokens
- **Phase 2**: 2-3 weeks (if Amazon requires LWA) → Fully certified

**Total**: 1-5 weeks depending on Amazon's requirements.
