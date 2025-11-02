# Apply alexa-oauth2 Security Fixes to MusicAssistantApple

**Date**: 2025-11-02
**Purpose**: Apply OAuth2+PKCE security improvements from alexa-oauth2 project to MusicAssistantApple Alexa integration
**Projects**:
- **Source**: `/Users/jason/projects/alexa-oauth2` (HA Alexa integration - OAuth CLIENT)
- **Target**: `/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple` (Music Assistant OAuth SERVER)

---

## Executive Summary

The alexa-oauth2 project implemented critical security fixes for Home Assistant's Alexa integration:
- ✅ OAuth2 + PKCE (RFC 7636) - prevents authorization code interception
- ✅ Fernet token encryption with PBKDF2 - prevents credential theft
- ✅ Nabu Casa Cloud routing - simplifies deployment
- ✅ Proper ADRs - documents architectural decisions

**MusicAssistantApple needs these SAME fixes** because:
1. The OAuth endpoints file (`alexa_oauth_endpoints.py`) currently has **NO actual user authentication** (line 378: `'user_id': 'test_user'`)
2. This is the "MFA provider impersonation" vulnerability - code PRETENDS to do Login with Amazon but doesn't
3. Tokens stored in-memory only (lost on restart)
4. No encrypted token storage

---

## Architecture Understanding

### alexa-oauth2 (HOME ASSISTANT INTEGRATION)

**Role**: OAuth2 **CLIENT** connecting TO Amazon
**Flow**: HA → Amazon LWA → User authenticates → Amazon returns tokens → HA uses tokens

**Files**:
- `custom_components/alexa/oauth.py` - AlexaOAuth2Implementation (PKCE)
- `custom_components/alexa/config_flow.py` - User setup flow
- `docs/00_ARCHITECTURE/ADR-001-REPLACE-LEGACY-INTEGRATION.md` - Security vulnerabilities
- `docs/00_ARCHITECTURE/ADR-002-TOKEN-ENCRYPTION-STRATEGY.md` - Fernet encryption
- `docs/00_ARCHITECTURE/ADR-003-USER-MIGRATION-STRATEGY.md` - Atomic migration

**Security Fixes Implemented**:
1. **PKCE** (oauth.py:45-65) - code_verifier → code_challenge → verify
2. **Nabu Casa routing** (oauth.py:97-107) - `async_get_redirect_uri()`
3. **Token encryption** (ADR-002) - Fernet + PBKDF2 600k iterations
4. **Proper ADRs** - Technology-agnostic decision records

---

### MusicAssistantApple (MUSIC ASSISTANT OAUTH SERVER)

**Role**: OAuth2 **SERVER** accepting connections FROM Alexa
**Flow**: Alexa → Music Assistant /authorize → User authenticates → MA returns code → Alexa exchanges for tokens

**Files**:
- `alexa_oauth_endpoints.py` - OAuth authorization + token endpoints
- Deployed to Music Assistant container on port 8096
- Public URL: https://haboxhill.tail1cba6.ts.net

**CRITICAL SECURITY GAPS**:
1. ❌ **NO ACTUAL USER AUTHENTICATION** (line 378):
   ```python
   'user_id': 'test_user',  # In production, from LWA auth
   ```
   Comment says "from LWA auth" but code just hardcodes `'test_user'`!

2. ❌ **NO LOGIN WITH AMAZON INTEGRATION**:
   - Line 17 comment: "User authenticates (passkey via Login with Amazon)"
   - But there's NO LWA OAuth flow implemented
   - Just shows consent screen and approves WITHOUT verifying identity

3. ❌ **TOKENS IN MEMORY ONLY** (lines 132-138):
   ```python
   auth_codes = {}  # Lost on restart
   tokens = {}      # Lost on restart
   ```

4. ❌ **NO TOKEN ENCRYPTION**:
   - Tokens stored as plaintext in dict
   - No Fernet encryption
   - No PBKDF2 key derivation

---

## What Needs to Be Applied

### Phase 1: Add Actual User Authentication (CRITICAL)

**Problem**: Code pretends user authenticated with Amazon but doesn't actually verify

**Current Code** (alexa_oauth_endpoints.py:366-381):
```python
# USER APPROVED! Move code from pending to active
print(f"✅ User approved! Moving code from pending to active...", flush=True)

# Generate final authorization code for Alexa
final_auth_code = generate_secure_token(32)

# Store in active auth_codes with full metadata
auth_codes[final_auth_code] = {
    'client_id': pending_data['client_id'],
    'code_challenge': pending_data['code_challenge'],
    'redirect_uri': pending_data['redirect_uri'],
    'user_id': 'test_user',  # In production, from LWA auth ← THIS IS THE PROBLEM!
    'expires_at': time.time() + AUTH_CODE_EXPIRY,
    'scope': pending_data['scope']
}
```

**Fix Required**: Integrate Login with Amazon (LWA) OAuth2 flow

**Option A: Use Amazon LWA for user authentication**:
1. Before showing consent screen, redirect user to Amazon LWA OAuth
2. User authenticates with Amazon (email/password + 2FA)
3. Amazon returns user_id token
4. NOW show consent screen with verified user_id
5. Generate authorization code bound to verified user

**Option B: Use Music Assistant's existing auth** (if available):
1. Check if Music Assistant has session/user auth
2. Require user to be logged into Music Assistant before authorizing
3. Bind authorization code to MA user session

**Recommendation**: Option A (LWA) because:
- Alexa Skill expects Amazon account authentication
- More secure (Amazon handles credentials)
- Aligns with HA Core Alexa integration pattern

---

### Phase 2: Add Token Encryption

**Apply from**: alexa-oauth2/docs/00_ARCHITECTURE/ADR-002-TOKEN-ENCRYPTION-STRATEGY.md

**Current** (alexa_oauth_endpoints.py:132-138):
```python
# In-memory storage for auth codes (production should use Redis or database)
auth_codes = {}

# Token storage (production should use Music Assistant's encrypted config storage)
tokens = {}
```

**Fix Required**:
1. Create `token_encryption.py` module based on ADR-002
2. Use Fernet (symmetric AES-128) + PBKDF2-HMAC-SHA512 (600k iterations)
3. Store encrypted tokens in Music Assistant config directory
4. Derive encryption key from system-level secret (MA config)

**Implementation** (new file `token_encryption.py`):
```python
"""Token encryption for Music Assistant Alexa OAuth server."""
import json
import os
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2

class TokenStore:
    """Encrypted token storage using Fernet + PBKDF2."""

    def __init__(self, config_dir: Path, passphrase: str):
        """Initialize with Music Assistant config directory."""
        self.storage_file = config_dir / ".alexa_tokens_v2.enc"
        self.fernet = self._derive_fernet(passphrase)

    def _derive_fernet(self, passphrase: str) -> Fernet:
        """Derive Fernet encryption key from passphrase using PBKDF2."""
        salt = b"music_assistant_alexa_oauth"  # Fixed salt for deterministic key
        kdf = PBKDF2(
            algorithm=hashes.SHA512(),
            length=32,  # 256 bits for Fernet
            salt=salt,
            iterations=600_000  # OWASP recommendation 2023
        )
        key = kdf.derive(passphrase.encode())
        return Fernet(key)

    def save_token(self, user_id: str, token_data: dict):
        """Encrypt and save token data."""
        # Load existing tokens
        all_tokens = self._load_all_tokens()

        # Update with new token
        all_tokens[user_id] = token_data

        # Encrypt and save
        plaintext = json.dumps(all_tokens).encode()
        encrypted = self.fernet.encrypt(plaintext)
        self.storage_file.write_bytes(encrypted)

        # Set file permissions to 0600 (owner read/write only)
        os.chmod(self.storage_file, 0o600)

    def load_token(self, user_id: str) -> dict | None:
        """Load and decrypt token for user."""
        all_tokens = self._load_all_tokens()
        return all_tokens.get(user_id)

    def _load_all_tokens(self) -> dict:
        """Load all encrypted tokens."""
        if not self.storage_file.exists():
            return {}

        try:
            encrypted = self.storage_file.read_bytes()
            plaintext = self.fernet.decrypt(encrypted)
            return json.loads(plaintext)
        except Exception:
            return {}  # Decryption failed or file corrupt
```

**Update `alexa_oauth_endpoints.py`**:
```python
from pathlib import Path
from token_encryption import TokenStore

# Initialize token store (global or passed to endpoints)
token_store = TokenStore(
    config_dir=Path("/data"),  # Music Assistant config directory
    passphrase=os.getenv("MA_ENCRYPTION_KEY", "default_key_change_me")
)

# Replace in-memory dicts with token_store calls:
# OLD: tokens[user_id] = {...}
# NEW: token_store.save_token(user_id, {...})

# OLD: token_data = tokens.get(user_id)
# NEW: token_data = token_store.load_token(user_id)
```

---

### Phase 3: Add PKCE Verification (Already Implemented!)

**Status**: ✅ ALREADY DONE in alexa_oauth_endpoints.py:616-633

The OAuth server already validates PKCE:
```python
# PKCE Verification (only if code_challenge was provided in authorization request)
if auth_data.get('code_challenge'):
    # PKCE was used, so code_verifier is required
    if not code_verifier:
        return web.json_response({
            'error': 'invalid_grant',
            'error_description': 'PKCE code_verifier required (code_challenge was provided in authorization)'
        }, status=400)

    # Validate PKCE: Hash code_verifier and compare to code_challenge
    computed_challenge = hash_code_verifier(code_verifier)
    if computed_challenge != auth_data['code_challenge']:
        return web.json_response({
            'error': 'invalid_grant',
            'error_description': 'PKCE verification failed: code_verifier does not match code_challenge'
        }, status=400)
```

**Good!** This correctly implements RFC 7636 PKCE validation.

---

### Phase 4: Create Proper ADRs

**Apply from**: alexa-oauth2/docs/00_ARCHITECTURE/

**Create in MusicAssistantApple**:

#### ADR-001: Replace Hardcoded User Authentication

**File**: `docs/00_ARCHITECTURE/ADR-001-LOGIN-WITH-AMAZON-REQUIRED.md`

**Decision**: Integrate Login with Amazon (LWA) OAuth2 for user authentication before authorization

**Rationale**:
- Security: Cannot trust implicit consent without verifying user identity
- Alexa Requirement: Alexa Skill expects Amazon account linkage
- Industry Standard: OAuth servers must verify user before issuing authorization codes

**Alternatives Rejected**:
- Hardcoded `'user_id': 'test_user'` (current) - Security vulnerability
- Music Assistant session auth only - Doesn't satisfy Alexa requirement
- No authentication - Complete security failure

**Implementation**:
```
/authorize → Check MA session → Redirect to Amazon LWA → User authenticates →
Amazon returns to /lwa_callback → Store user_id → Show consent screen →
User approves → Issue authorization code bound to verified user_id
```

---

#### ADR-002: Token Encryption Strategy

**File**: `docs/00_ARCHITECTURE/ADR-002-TOKEN-ENCRYPTION-STRATEGY.md`

**Decision**: Use Fernet (AES-128-CBC) + PBKDF2-HMAC-SHA512 (600k iterations) for token encryption

**Copy from**: alexa-oauth2/docs/00_ARCHITECTURE/ADR-002-TOKEN-ENCRYPTION-STRATEGY.md

**Adaptations for Music Assistant**:
- Passphrase: Derive from Music Assistant's existing encryption key (if available)
- Storage location: `/data/.alexa_tokens_v2.enc`
- File permissions: 0600 (owner read/write only)
- Rotation: Support key rotation by versioning (v1, v2, etc.)

---

#### ADR-003: Persistent Token Storage

**File**: `docs/00_ARCHITECTURE/ADR-003-PERSISTENT-TOKEN-STORAGE.md`

**Decision**: Store tokens in encrypted file, NOT in-memory dicts

**Problem with Current**:
```python
auth_codes = {}  # Lost on Music Assistant restart
tokens = {}      # Lost on Music Assistant restart
```

**Solution**:
- Authorization codes: Short-lived (5 min), can stay in-memory
- Access tokens: 1 hour, should persist across restarts
- Refresh tokens: 90 days, MUST persist across restarts

**Implementation**:
- Use `TokenStore` class (from Phase 2)
- Automatically load tokens on startup
- Periodically save to disk (every token operation)
- Clean up expired tokens on load

---

### Phase 5: Configuration Simplification (Optional)

**Apply from**: alexa-oauth2/SIMPLIFIED_CONFIG_FLOW.md

This is optional for Music Assistant because:
- MA OAuth server uses environment variables (already simple)
- No user-facing config flow (server-side only)
- Credentials managed by MA admin, not end users

**Current Config** (environment variables):
```bash
ALEXA_CLIENT_ID=amazon-alexa
ALEXA_CLIENT_SECRET=(optional for public PKCE client)
ALEXA_REDIRECT_URI=https://pitangui.amazon.com/auth/o2/callback
```

**Keep as-is** - This is already simplified compared to HA integration

---

## Implementation Priority

### P0: CRITICAL SECURITY (Deploy within 1 week)

1. **Add Login with Amazon authentication** (Phase 1)
   - Cannot ship without actual user verification
   - Current code is a placeholder that would fail security audit

2. **Add token encryption** (Phase 2)
   - Prevents credential theft if container compromised
   - Required for production deployment

### P1: STABILITY (Deploy within 1 month)

3. **Persistent token storage** (Phase 3 - part of Phase 2)
   - Tokens survive Music Assistant restarts
   - Better user experience (no re-auth after restart)

4. **Create ADRs** (Phase 4)
   - Documents security decisions
   - Required for code review / security audit

### P2: ENHANCEMENTS (Backlog)

5. **Automated testing**
   - Unit tests for PKCE validation
   - Integration tests for OAuth flow
   - Security tests for token encryption

6. **Monitoring and logging**
   - Track failed auth attempts
   - Log PKCE validation failures
   - Alert on token decryption failures

---

## File Mapping: alexa-oauth2 → MusicAssistantApple

| alexa-oauth2 (Source) | MusicAssistantApple (Target) | Action |
|----------------------|----------------------------|--------|
| `custom_components/alexa/oauth.py` | Reference for CLIENT-side PKCE | Study patterns, don't copy (different role) |
| `docs/00_ARCHITECTURE/ADR-001-REPLACE-LEGACY-INTEGRATION.md` | `docs/00_ARCHITECTURE/ADR-001-LOGIN-WITH-AMAZON-REQUIRED.md` | **Create** - Adapt for OAuth SERVER context |
| `docs/00_ARCHITECTURE/ADR-002-TOKEN-ENCRYPTION-STRATEGY.md` | `docs/00_ARCHITECTURE/ADR-002-TOKEN-ENCRYPTION-STRATEGY.md` | **Copy** - Fernet+PBKDF2 applies to both CLIENT and SERVER |
| `docs/00_ARCHITECTURE/ADR-003-USER-MIGRATION-STRATEGY.md` | `docs/00_ARCHITECTURE/ADR-003-PERSISTENT-TOKEN-STORAGE.md` | **Create** - In-memory → Encrypted file migration |
| N/A | `token_encryption.py` | **Create** - Implement TokenStore class |
| N/A | `lwa_auth.py` | **Create** - Login with Amazon OAuth integration |

---

## Testing Strategy

### Before Implementation

1. **Audit current OAuth flow**:
   ```bash
   # Test current implementation (insecure)
   curl -X GET "https://haboxhill.tail1cba6.ts.net/alexa/authorize?response_type=code&client_id=amazon-alexa&redirect_uri=https://pitangui.amazon.com/auth/o2/callback&state=test123&code_challenge=abc&code_challenge_method=S256"
   ```

   Expected: Consent screen appears WITHOUT any user authentication

2. **Document security gap**:
   - User sees consent screen
   - User clicks "Approve"
   - System generates authorization code
   - ❌ **NO verification that user is who they claim to be!**

### After Phase 1 (LWA Auth)

1. **Test LWA integration**:
   ```bash
   # Should redirect to Amazon for login BEFORE consent screen
   curl -L "https://haboxhill.tail1cba6.ts.net/alexa/authorize?..."
   ```

   Expected: 302 redirect to `amazon.com/ap/oa` (Amazon login)

2. **Verify user_id binding**:
   - Check that authorization code contains REAL Amazon user_id
   - Not hardcoded `'test_user'`

### After Phase 2 (Token Encryption)

1. **Verify encrypted storage**:
   ```bash
   # Check tokens file is encrypted (not readable as JSON)
   cat /data/.alexa_tokens_v2.enc
   ```

   Expected: Binary ciphertext, not plaintext JSON

2. **Verify file permissions**:
   ```bash
   ls -la /data/.alexa_tokens_v2.enc
   ```

   Expected: `-rw------- 1 mass mass` (0600 permissions)

---

## Success Criteria

**Phase 1 Complete When**:
- [ ] `/alexa/authorize` redirects to Amazon LWA for authentication
- [ ] User must login with Amazon before seeing consent screen
- [ ] Authorization codes bound to verified Amazon user_id
- [ ] Hardcoded `'user_id': 'test_user'` removed from codebase

**Phase 2 Complete When**:
- [ ] Tokens encrypted with Fernet before storage
- [ ] PBKDF2 key derivation with 600k iterations
- [ ] File permissions set to 0600 (owner-only)
- [ ] Tokens persist across Music Assistant restarts

**Production-Ready When**:
- [ ] All P0 and P1 items completed
- [ ] ADRs created and reviewed
- [ ] Security audit passed (internal or external)
- [ ] Integration tests passing
- [ ] Documentation updated

---

## Related Documents

### In alexa-oauth2:
- [ADR-001: Replace Legacy Integration](file:///Users/jason/projects/alexa-oauth2/docs/00_ARCHITECTURE/ADR-001-REPLACE-LEGACY-INTEGRATION.md)
- [ADR-002: Token Encryption Strategy](file:///Users/jason/projects/alexa-oauth2/docs/00_ARCHITECTURE/ADR-002-TOKEN-ENCRYPTION-STRATEGY.md)
- [ADR-003: User Migration Strategy](file:///Users/jason/projects/alexa-oauth2/docs/00_ARCHITECTURE/ADR-003-USER-MIGRATION-STRATEGY.md)
- [SIMPLIFIED_CONFIG_FLOW.md](file:///Users/jason/projects/alexa-oauth2/SIMPLIFIED_CONFIG_FLOW.md)

### To Create in MusicAssistantApple:
- `docs/00_ARCHITECTURE/ADR-001-LOGIN-WITH-AMAZON-REQUIRED.md`
- `docs/00_ARCHITECTURE/ADR-002-TOKEN-ENCRYPTION-STRATEGY.md`
- `docs/00_ARCHITECTURE/ADR-003-PERSISTENT-TOKEN-STORAGE.md`
- `token_encryption.py` (new module)
- `lwa_auth.py` (new module for Login with Amazon integration)

---

**Next Steps**:
1. Review this assessment with user
2. Prioritize P0 tasks (LWA auth + token encryption)
3. Create ADR-001 for Login with Amazon requirement
4. Implement `lwa_auth.py` module
5. Implement `token_encryption.py` module
6. Update `alexa_oauth_endpoints.py` to use both
7. Test end-to-end OAuth flow with real Amazon authentication
8. Deploy to Music Assistant container
9. Security audit and verification

---

**Document Status**: DRAFT
**Last Updated**: 2025-11-02
**Author**: Claude Code (Sonnet 4.5)
**Review Required**: User approval before implementation
