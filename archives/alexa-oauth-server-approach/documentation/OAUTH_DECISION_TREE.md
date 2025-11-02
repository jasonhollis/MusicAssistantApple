# OAuth Security Architecture - Decision Tree
**Date**: 2025-11-02

---

## Quick Decision Flowchart

```
┌─────────────────────────────────────────────────────────────┐
│ START: OAuth Server Security Hardening                      │
│ Current: user_id='test_user', in-memory tokens              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Q1: Is OAuth currently in production with active users?     │
└─────────────────────────┬───────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼ NO (Beta/Phase 2)     ▼ YES (Production)
    ┌─────────────────────┐   ┌─────────────────────────┐
    │ → Breaking Change   │   │ → Zero-Downtime         │
    │   Migration         │   │   Dual-Mode Migration   │
    │   (Simple)          │   │   (Complex)             │
    └──────────┬──────────┘   └───────────┬─────────────┘
               │                          │
               │                          │
               └──────────┬───────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Q2: What is Music Assistant's user model?                   │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┴────────────────┐
          │                                │
          ▼ Single-user                    ▼ Multi-user
    ┌─────────────────┐            ┌─────────────────────┐
    │ → Device Auth   │            │ → LWA Integration   │
    │   (Phase 1)     │            │   (Immediate)       │
    └────────┬────────┘            └──────────┬──────────┘
             │                                │
             │                                │
             └────────────┬───────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Q3: What storage infrastructure is available?               │
└─────────────────────────┬───────────────────────────────────┘
                          │
      ┌───────────────────┼────────────────────┐
      │                   │                    │
      ▼ MA Config         ▼ Can deploy        ▼ No infra
   ┌──────────┐        ┌──────────┐        ┌──────────┐
   │ → Use MA │        │ → PG +   │        │ → SQLite │
   │   Native │        │   Vault  │        │ + Fernet │
   │ ✅ BEST  │        │ ⚠️ Heavy │        │ ⚠️ OK    │
   └────┬─────┘        └────┬─────┘        └────┬─────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ DECISION: Phase 1 Implementation                            │
│                                                              │
│ ✅ Persistent Encrypted Storage (Music Assistant Config)    │
│ ✅ Device Authorization (Simple Consent Screen)             │
│ ✅ Breaking Change Migration (Beta Acceptable)              │
│                                                              │
│ Timeline: 1-2 weeks                                          │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Q4: Does Amazon require LWA for certification?              │
│ (Contact Amazon Developer Support to validate)              │
└─────────────────────────┬───────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼ YES                   ▼ NO
    ┌─────────────────────┐   ┌─────────────────────┐
    │ → Phase 2:          │   │ → Stay on Phase 1   │
    │   LWA Integration   │   │   (Device Auth OK)  │
    │   (2-3 weeks)       │   │                     │
    └──────────┬──────────┘   └──────────┬──────────┘
               │                         │
               └──────────┬──────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ END: Production-Ready OAuth Server                          │
│                                                              │
│ ✅ Persistent encrypted tokens                              │
│ ✅ Survives container restarts                              │
│ ✅ Amazon certified (if LWA required)                       │
│ ✅ Secure, maintainable, scalable                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Decision Matrix: Storage Options

| Criteria | In-Memory | MA Config | PostgreSQL+Vault | SQLite+Fernet |
|----------|-----------|-----------|------------------|---------------|
| **Persistence** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **Encryption** | ❌ No | ✅ Yes | ✅ Yes | ✅ Yes |
| **Operational Overhead** | ✅ None | ✅ None | ❌ High | ⚠️ Low |
| **Aligns with MA Patterns** | ❌ No | ✅ Yes | ❌ No | ⚠️ Partial |
| **Backup/Restore** | ❌ N/A | ✅ Simple | ⚠️ Complex | ✅ Simple |
| **Key Rotation** | ❌ N/A | ⚠️ Manual | ✅ Auto | ⚠️ Manual |
| **Audit Trail** | ❌ No | ⚠️ HA Logs | ✅ Built-in | ❌ No |
| **Deployment Model Fit** | ❌ No | ✅ Perfect | ❌ Overkill | ⚠️ OK |
| **Recommendation** | ❌ Not viable | ✅ **RECOMMENDED** | ❌ Over-engineered | ⚠️ Fallback |

**Winner**: **Music Assistant Config** (zero overhead, proven, perfect fit)

---

## Decision Matrix: Authentication Strategies

| Criteria | LWA Now | Device Auth Now | Phased (Device→LWA) |
|----------|---------|-----------------|---------------------|
| **Time to Production** | ❌ 2-3 weeks | ✅ 1-2 weeks | ✅ 1-2 weeks |
| **Amazon Certification** | ✅ Guaranteed | ⚠️ Unknown | ✅ Upgradable |
| **Complexity** | ❌ High | ✅ Low | ⚠️ Medium |
| **Aligns with Single-User** | ⚠️ Overkill | ✅ Perfect | ✅ Good |
| **External Dependencies** | ❌ LWA API | ✅ None | ✅ None (Phase 1) |
| **User Experience** | ⚠️ Amazon login | ✅ Click approve | ✅ Simple (Phase 1) |
| **Migration Risk** | ✅ None | ⚠️ May need rework | ⚠️ Planned migration |
| **Recommendation** | ❌ Defer | ⚠️ Risky alone | ✅ **RECOMMENDED** |

**Winner**: **Phased Approach** (validate first, upgrade if needed)

---

## Decision Matrix: Migration Strategies

| Criteria | Breaking Change | Dual-Mode | Auto-Migration |
|----------|----------------|-----------|----------------|
| **Implementation Complexity** | ✅ Simple | ❌ High | ⚠️ Medium |
| **User Disruption** | ⚠️ Re-link | ✅ None | ✅ Minimal |
| **Technical Debt** | ✅ None | ❌ High | ⚠️ Medium |
| **Acceptable for Beta?** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Acceptable for Prod?** | ❌ No | ✅ Yes | ✅ Yes |
| **Current OAuth Status** | ✅ Beta | ❌ Prod | ⚠️ Either |
| **Time to Deploy** | ✅ 1 day | ❌ 1 week | ⚠️ 3 days |
| **Recommendation** | ✅ **RECOMMENDED** (Beta) | ❌ Over-engineered | ❌ Over-engineered |

**Winner**: **Breaking Change** (OAuth is beta, clean foundation)

---

## Risk-Based Decision Tree

```
┌────────────────────────────────────────────────────────┐
│ Is the risk ACCEPTABLE?                                │
└────────────────────┬───────────────────────────────────┘
                     │
     ┌───────────────┴────────────────┐
     │                                │
     ▼ HIGH RISK                      ▼ LOW/MEDIUM RISK
┌─────────────────┐          ┌──────────────────────┐
│ Examples:       │          │ Examples:            │
│ - Token leakage │          │ - User re-link beta  │
│ - Data loss     │          │ - LWA Phase 2 rework │
│ - Cert failure  │          │ - Storage perf       │
└────────┬────────┘          └──────────┬───────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐          ┌──────────────────────┐
│ → MUST MITIGATE │          │ → ACCEPT & MONITOR   │
│   IMMEDIATELY   │          │   (Log + Alert)      │
└─────────────────┘          └──────────────────────┘

High-Risk Items Requiring Mitigation:
✅ Token encryption (Fernet)
✅ Persistent storage (MA Config)
✅ Key management (Docker/HA secrets)
✅ Token redaction in logs

Low-Risk Items to Monitor:
⏳ Amazon cert requirements (contact support)
⏳ User migration completion (log metrics)
⏳ Storage performance (monitor latency)
```

---

## Implementation Path Selector

**Answer these 3 questions to determine your path:**

### Q1: Is OAuth currently deployed with active users?
- **A) No (Beta/Testing)** → Breaking Change Migration ✅
- **B) Yes (Production)** → Dual-Mode Migration ⚠️

### Q2: Can you contact Amazon Developer Support this week?
- **A) Yes** → Start Phase 1, get LWA answer in parallel ✅
- **B) No** → Implement LWA now (safer) ⚠️

### Q3: Do you need Music Assistant to support multiple users?
- **A) No (Single-user home automation)** → Device Auth Phase 1 ✅
- **B) Yes (Multi-user service)** → LWA Integration immediate ⚠️

**Most Common Path** (Music Assistant typical deployment):
- Q1: A (Beta) → Breaking Change
- Q2: A (Contact Amazon) → Phase 1 + Parallel validation
- Q3: A (Single-user) → Device Auth

**Result**: **Phase 1 Implementation (Device Auth + MA Config Storage)**

---

## Timeline Estimator

```
Week 1: Validation & Prototype
├─ Day 1-2: Contact Amazon Support, review MA code
├─ Day 3-5: Implement TokenStore prototype
└─ End Week 1: Decision on Phase 2 (LWA required?)

Week 2-3: Implementation
├─ Replace in-memory storage
├─ Add encryption
├─ Device authorization flow
├─ Testing & security review
└─ End Week 2: Phase 1 deployment

Week 4-6: Phase 2 (IF LWA REQUIRED)
├─ Implement LWA OAuth client
├─ Add LWA callback endpoint
├─ Update consent screen
├─ Amazon certification testing
└─ End Week 6: Full production deployment

Total Timeline:
- Phase 1 Only: 2-3 weeks ✅
- Phase 1 + Phase 2: 5-6 weeks
```

---

## Quick Reference: What Should I Do Right Now?

### Immediate (This Week)
1. ✅ **Contact Amazon Developer Support**
   - Email: alexa-dev-support@amazon.com
   - Question: "Does Music Assistant smart home skill require Login with Amazon (LWA) for certification?"
   - Document response

2. ✅ **Read Music Assistant Spotify Provider Code**
   - File: `server-2.6.0/music_assistant/providers/spotify/`
   - Focus: How does it store OAuth tokens?
   - Validate: Can we reuse this pattern?

3. ✅ **Prototype TokenStore Class**
   - Implement basic encryption with Fernet
   - Test write/read from MA config
   - Validate persistence across container restart

### Week 2-3: Build
1. Replace `auth_codes = {}` with `TokenStore` (line 134)
2. Replace `tokens = {}` with `TokenStore` (line 138)
3. Update `user_id='test_user'` logic (line 378)
4. Add encryption key management
5. Test restart scenarios

### Week 4: Deploy
1. Security review
2. Add migration notice
3. Deploy to production
4. Monitor logs for issues

---

## Success Criteria Checklist

**Phase 1 Complete When**:
- [ ] Container restart preserves user sessions
- [ ] Tokens encrypted at rest (verified with hex dump)
- [ ] No `test_user` in logs after migration
- [ ] OAuth flow success rate >99%
- [ ] Encryption key stored securely (not in code)
- [ ] Backup/restore procedure documented
- [ ] Migration notice displayed on startup

**Phase 2 Complete When** (if required):
- [ ] Users log in via Amazon account
- [ ] LWA JWT signature validation working
- [ ] Alexa Skill certification passed
- [ ] Zero-downtime migration from Phase 1
- [ ] LWA API circuit breaker tested

---

## Key Takeaways

1. **Storage**: Use Music Assistant's native config (zero overhead, proven)
2. **Authentication**: Phase 1 = Device auth, Phase 2 = LWA (if Amazon requires)
3. **Migration**: Breaking change acceptable (OAuth is beta)
4. **Timeline**: 1-2 weeks Phase 1, +2-3 weeks Phase 2 (conditional)
5. **Next Action**: Contact Amazon Developer Support to validate LWA requirement

**Bottom Line**: Start with Phase 1 (simple, fast, works). Upgrade to Phase 2 only if Amazon requires LWA for certification.
