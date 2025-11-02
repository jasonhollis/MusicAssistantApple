# Alexa Skill OAuth - Quick Decision Guide
**Date**: 2025-10-25
**Purpose**: 1-page executive summary for rapid decision-making
**Full Research**: See ALEXA_SKILL_OAUTH_RESEARCH_2025.md (26,000+ words)

---

## The Question

Should we build a custom Alexa skill with OAuth instead of using the current alexapy reverse-engineered approach?

## The Answer

**YES - Build Alexa Skill for MVP** (1-2 weeks, 40-60 hours)

---

## Why Build Alexa Skill?

### Security Improvement
- ✅ **Eliminates all 8 critical vulnerabilities** in current alexapy implementation
- ✅ **No RCE risk** (removes pickle deserialization)
- ✅ **No credential storage** (OAuth redirect flow - user logs in with Amazon)
- ✅ **Official Amazon API** (supported, documented, SLA)

### Current State (alexapy)
- 🔴 RCE vulnerability via pickle deserialization
- 🔴 Plaintext credentials in Music Assistant config
- 🔴 Reverse-engineered API (breaks frequently)
- 🔴 High maintenance burden

### Proposed State (Alexa Skill + OAuth)
- ✅ Industry-standard OAuth 2.0 Authorization Code Grant
- ✅ User credentials never touch Music Assistant
- ✅ Tokens encrypted and managed by Amazon
- ✅ Automatic token refresh handled by Alexa

---

## What's Involved?

### MVP Scope (Proof-of-Concept)
**Single Intent**: "Alexa, ask Music Assistant what's playing"
**Result**: Validates OAuth flow works, proves security improvements

### Components Needed
1. **Alexa Skill** (Developer Console) - 2-3 hours setup
2. **AWS Lambda Function** (Python) - 3-5 hours development
3. **Login with Amazon** (LWA OAuth) - 1-2 hours configuration
4. **Music Assistant API** (token validation) - 3-5 hours backend work
5. **Testing & Debugging** - 3-5 hours integration

### Total Time
- **Beginner** (learning ASK SDK): 40-60 hours (1-2 weeks)
- **Intermediate** (some AWS experience): 16-26 hours (3-5 days)
- **Expert** (Alexa/AWS pro): 8-12 hours (1-2 days)

---

## Key Constraints

### The Big One: HTTPS Requirement
**Skill endpoint must be publicly accessible on port 443**

**Options**:
1. ✅ **AWS Lambda** (recommended) - free tier, auto-scaling, built-in HTTPS
2. ✅ **ngrok tunnel** (development) - $8/month for fixed URL
3. ⚠️ **Self-hosted server** - requires public IP, SSL certificate management
4. ❌ **Localhost** - NOT supported (must tunnel via ngrok or deploy to cloud)

**Recommendation**: Use AWS Lambda (free tier handles 1M requests/month).

### OAuth Endpoint
**Can be localhost for development** (via ngrok), **must be public for production**

**Simplest Path**: Use Login with Amazon (LWA) - Amazon hosts OAuth for you.

---

## Decision Matrix

| Approach | Security | Effort | Maintenance | Cost | Recommendation |
|----------|----------|--------|-------------|------|----------------|
| **Keep alexapy (as-is)** | 🔴 CRITICAL | ✅ Low (done) | 🔴 HIGH | $0 | ❌ NOT SAFE |
| **Fix alexapy security** | 🟡 MEDIUM | 🟡 Medium (2-4 weeks) | 🟡 MEDIUM | $0 | ⚠️ Short-term only |
| **Alexa Skill MVP** | ✅ HIGH | 🟡 Medium (1-2 weeks) | ✅ LOW | ~$0-5/mo | ✅ **RECOMMENDED** |
| **Alexa Skill (Full)** | ✅ HIGH | 🔴 HIGH (4-6 weeks) | ✅ LOW | ~$0-5/mo | ✅ Production goal |

---

## Recommended Path

### Week 1: MVP Development
1. **Day 1**: Setup (AWS account, Developer Console, LWA security profile)
2. **Day 2-3**: Build skill (single intent, Lambda function)
3. **Day 4**: Configure OAuth (LWA account linking)
4. **Day 5**: Test end-to-end, document findings

**Deliverable**: Working proof-of-concept that validates OAuth security improvements.

### Week 2-4: Production Features (Optional)
1. Full interaction model (play, pause, skip, search)
2. AudioPlayer implementation (music streaming)
3. Error handling and logging
4. Unit tests

**Deliverable**: Production-ready private skill.

### Month 2-3: Public Release (Optional)
1. Skill certification preparation
2. Privacy policy and terms of service
3. Submit to Alexa Skills Store

**Deliverable**: Publicly available skill.

---

## Critical Questions

### 1. Can Music Assistant API be exposed to public internet?
- **If NO**: Use ngrok tunnel (development) or keep alexapy
- **If YES**: Deploy Lambda or self-hosted skill endpoint

### 2. Are you comfortable with AWS Lambda?
- **If NO**: Consider Alexa-Hosted Skills (Amazon manages hosting)
- **If YES**: Lambda is the recommended path

### 3. What's your security risk tolerance?
- **If HIGH** (accept RCE risk): Keep alexapy as-is
- **If MEDIUM**: Fix alexapy security issues (2-4 weeks)
- **If LOW**: Build Alexa skill (1-2 weeks MVP)

### 4. Is this for personal use or public distribution?
- **Personal**: Private skill (no certification, faster)
- **Public**: Add 4-8 weeks for certification process

---

## Cost Breakdown

| Item | Cost | Required? |
|------|------|-----------|
| AWS Lambda (free tier) | $0/month (1M requests) | ✅ Yes |
| Alexa Developer Account | $0 | ✅ Yes |
| Login with Amazon | $0 | ✅ Yes |
| ngrok Pro (development) | $8/month | ⚠️ Optional (free tier works) |
| SSL Certificate (self-hosted) | $0 (Let's Encrypt) | ❌ No (use Lambda) |
| **TOTAL** | **$0-8/month** | Development: $0-8, Production: ~$0 |

---

## What You Get

### MVP (1-2 weeks)
- ✅ Secure OAuth 2.0 account linking
- ✅ No credentials stored in Music Assistant
- ✅ Single working intent (proof-of-concept)
- ✅ Validation that approach works

### Production (4-6 weeks)
- ✅ Full music control (play, pause, skip, volume, search)
- ✅ AudioPlayer for streaming
- ✅ Comprehensive error handling
- ✅ Unit tests and monitoring

### Public Release (8-12 weeks)
- ✅ Published in Alexa Skills Store
- ✅ Available to all users
- ✅ Privacy policy and legal compliance

---

## Next Steps (Choose One)

### Option A: Build Alexa Skill MVP (RECOMMENDED)
1. ✅ Create AWS account (if don't have one)
2. ✅ Create Alexa Developer Console account
3. ✅ Set up development environment (Python, ask-sdk)
4. ✅ Follow implementation guide in ALEXA_SKILL_OAUTH_RESEARCH_2025.md
5. ✅ Target: Working MVP in 1-2 weeks

### Option B: Fix alexapy Security Issues
1. ✅ Implement Priority 1 fixes from ALEXA_AUTH_EXECUTIVE_SUMMARY.md
2. ✅ Replace pickle with encrypted JSON
3. ✅ Set file permissions to 0600
4. ✅ Add input validation
5. ✅ Target: Security hardening in 2-4 weeks

### Option C: Do Nothing (NOT RECOMMENDED)
- ⚠️ Accept 8 critical security vulnerabilities
- ⚠️ Accept RCE risk via pickle deserialization
- ⚠️ Accept frequent breakage from Amazon API changes
- ❌ **Not recommended for production use**

---

## The Bottom Line

**Build the Alexa skill.**

- **Why**: Eliminates critical security vulnerabilities, uses official API, better long-term maintainability
- **When**: Start this week (1-2 weeks for MVP)
- **How**: AWS Lambda + Login with Amazon + Python ASK SDK
- **Cost**: ~$0-5/month (AWS free tier)
- **Risk**: Low (can abandon if doesn't work, fall back to alexapy)
- **Reward**: High (production-ready secure architecture)

**First Step**: Read Section 4 of ALEXA_SKILL_OAUTH_RESEARCH_2025.md ("Minimum Viable Alexa Skill") for detailed implementation guide.

---

**Document Version**: 1.0
**Created**: 2025-10-25
**Full Research**: ALEXA_SKILL_OAUTH_RESEARCH_2025.md (70+ pages)
**Related**: ALEXA_AUTH_EXECUTIVE_SUMMARY.md (current security vulnerabilities)
