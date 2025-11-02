# Alexa Authentication - Quick Reference Card
**For Developers Working on Security Fixes**

---

## 🔴 Top 3 Critical Issues

### 1. Pickle RCE Vulnerability
**File**: `alexa/__init__.py:218-223`
**Risk**: Remote Code Execution
**Fix**:
```python
# BEFORE (INSECURE):
await asyncio.to_thread(cookie_jar.save, login._cookiefile[0])  # Pickle

# AFTER (SECURE):
from cryptography.fernet import Fernet
encrypted = fernet.encrypt(json.dumps(cookies).encode())
Path(cookie_path).write_bytes(encrypted)
os.chmod(cookie_path, 0o600)
```

---

### 2. Plaintext Credentials
**File**: `alexa/__init__.py:82-86`
**Risk**: Memory dumps expose passwords + OTP seeds
**Fix**:
```python
# AFTER AUTH, WIPE CREDENTIALS:
secure_delete(password)
secure_delete(otp_secret)
del password, otp_secret

# OR: Use system keyring (better)
import keyring
keyring.set_password("music_assistant", "alexa_password", password)
```

---

### 3. World-Readable Cookie Files
**File**: `alexa/__init__.py:211-213`
**Risk**: Other users can steal session cookies
**Fix**:
```python
# BEFORE:
await asyncio.to_thread(os.makedirs, cookie_dir, exist_ok=True)

# AFTER:
await asyncio.to_thread(os.makedirs, cookie_dir, mode=0o700, exist_ok=True)
# Directory: drwx------ (owner-only)
# Files: -rw------- (0o600)
```

---

## 🛠️ File Locations

```
server-2.6.0/music_assistant/providers/alexa/
├── __init__.py              # Main provider (438 lines)
│   ├── Lines 65-202:  get_config_entries() - Auth flow
│   ├── Lines 80-141:  Proxy setup and auth
│   ├── Lines 205-226: save_cookie() - INSECURE PICKLE
│   ├── Lines 267-283: loaded_in_mass() - Session init
│   └── Lines 329-437: Player control commands
│
├── manifest.json            # Dependencies: alexapy==1.29.5
└── icon.svg / icon_monochrome.svg

server-2.6.0/music_assistant/helpers/
└── auth.py                  # AuthenticationHelper (107 lines)
    └── Lines 22-107: Callback handler for OAuth-style flow
```

---

## 🔍 Authentication Flow (5-Minute Explanation)

```
1. USER CLICKS "AUTHENTICATE"
   ├─> Collects: email, password, OTP secret, Amazon domain
   └─> Triggers: CONF_ACTION_AUTH

2. MUSIC ASSISTANT SETS UP PROXY
   ├─> Creates AlexaLogin(email, password, otp_secret)  ⚠️ PLAINTEXT
   ├─> Creates AlexaProxy(login, proxy_url)
   └─> Registers routes: /alexa/auth/proxy/* (GET/POST)

3. USER AUTHENTICATES VIA PROXY
   ├─> Browser opens proxy URL
   ├─> AlexaProxy forwards to Amazon login
   ├─> User enters credentials on Amazon page
   ├─> Amazon sets cookies in AlexaLogin session
   └─> Success detected: "Successfully logged in" string ⚠️ FRAGILE

4. MUSIC ASSISTANT VALIDATES & SAVES
   ├─> Calls: login.test_loggedin()  (validates cookies)
   ├─> Saves cookies: cookie_jar.save(pickle_file) ⚠️ INSECURE
   └─> Unregisters proxy routes

5. SUBSEQUENT SESSIONS
   ├─> Loads cookies: login.load_cookie()  ⚠️ PICKLE DESERIALIZE
   ├─> Calls: login.login(cookies=loaded_cookies)
   └─> If valid: Fetches device list, registers players
```

---

## 🐛 Common Breakage Points

| What Breaks | Why | How to Detect |
|-------------|-----|---------------|
| **Amazon domain changes** | New login page HTML | User can't auth, "Successfully logged in" not found |
| **Cookie format changes** | Amazon backend update | Auth succeeds but API calls fail |
| **CAPTCHA updates** | New CAPTCHA type | Proxy gets stuck, timeout error |
| **alexapy version conflict** | aiohttp version mismatch | ImportError or AttributeError |
| **Cookie expiration** | No token refresh | "Device unavailable" errors |
| **Regional differences** | amazon.co.uk vs .com | Auth works on .com, fails on .co.uk |

---

## 🔐 Security Checklist

**Before Deploying Fix**:
- [ ] No `pickle.load()` or `pickle.dump()` in code
- [ ] All credential storage uses encryption (Fernet or system keyring)
- [ ] File permissions explicitly set: `os.chmod(path, 0o600)`
- [ ] Directory permissions: `os.makedirs(path, mode=0o700)`
- [ ] Credentials cleared from memory after use
- [ ] No plaintext credentials in logs (check debug mode)
- [ ] Error messages don't leak sensitive info
- [ ] External API calls use HTTPS (not HTTP)

**Testing Checklist**:
- [ ] Test with invalid credentials (should fail gracefully)
- [ ] Test with expired cookies (should refresh or prompt re-auth)
- [ ] Test file permissions: `ls -la ~/.local/share/music_assistant/.alexa/`
- [ ] Test pickle vulnerability (try loading malicious pickle)
- [ ] Test memory: No plaintext passwords in `ps aux | grep music_assistant`

---

## 🧪 Testing Snippets

### Test File Permissions
```bash
# Check directory permissions (should be 700)
stat -f "%OLp" ~/.local/share/music_assistant/.alexa/
# Expected: 700

# Check cookie file permissions (should be 600)
stat -f "%OLp" ~/.local/share/music_assistant/.alexa/*.pickle
# Expected: 600
```

### Test Pickle Vulnerability (BEFORE FIX)
```python
# Create malicious pickle (DO NOT RUN IN PROD)
import pickle, os

class Exploit:
    def __reduce__(self):
        return (os.system, ('echo VULNERABLE > /tmp/pickle_test',))

with open('test_cookie.pickle', 'wb') as f:
    pickle.dump(Exploit(), f)

# If loading this file creates /tmp/pickle_test → VULNERABLE
```

### Test Token Refresh
```python
# Manually expire cookies, check if refresh works
import time

# Load provider
provider = mass.providers.get("alexa_instance_id")

# Check login validity
assert await provider.login.test_loggedin()

# Invalidate session (simulate expiration)
provider.login._session.cookie_jar.clear()

# Should trigger refresh or re-auth (after fix)
await provider.ensure_authenticated()  # Add this method
```

---

## 📚 Dependency Documentation

### alexapy Library
- **Version**: 1.29.5 (pinned)
- **Docs**: https://alexapy.readthedocs.io/en/stable/
- **GitHub**: https://github.com/alandtse/alexapy
- **Issues**: https://github.com/alandtse/alexa_media_player/issues

### Key Classes
```python
from alexapy import AlexaLogin, AlexaProxy, AlexaAPI

# AlexaLogin: Manages Amazon session
login = AlexaLogin(url, email, password, otp_secret, outputpath)
await login.login(cookies=None)  # Initial auth
await login.test_loggedin()       # Validate session
await login.load_cookie()         # Load from disk
login._session                    # aiohttp.ClientSession (private!)

# AlexaProxy: Proxy-based authentication
proxy = AlexaProxy(login, proxy_url)
await proxy.all_handler(request)  # Handle proxy requests

# AlexaAPI: Device control
api = AlexaAPI(device_object, login)
await api.play()
await api.pause()
await api.stop()
await api.set_volume(level)
await api.get_state()
await api.run_custom(text)
```

---

## 🚨 Error Handling Patterns

### BEFORE (BAD):
```python
try:
    await auth_helper.authenticate(proxy_url)
except KeyError:
    pass  # Silent failure
except Exception as error:
    raise LoginFailed(f"Failed: '{error}'")  # Loses context
```

### AFTER (GOOD):
```python
try:
    await auth_helper.authenticate(proxy_url)
    if not await login.test_loggedin():
        raise LoginFailed("Session validation failed")

except asyncio.TimeoutError:
    _LOGGER.warning("Authentication timed out after 60s")
    raise LoginFailed("Timeout - please try again") from None

except aiohttp.ClientError as err:
    _LOGGER.exception("Network error during auth")
    raise LoginFailed(f"Network error: {err}") from err

except Exception as err:
    _LOGGER.exception("Unexpected auth error")
    raise LoginFailed(
        f"Authentication failed ({type(err).__name__}). "
        f"See logs or visit https://music-assistant.io/help/alexa"
    ) from err
```

---

## 🎯 Quick Wins (Low-Hanging Fruit)

### 1. Add Input Validation (30 minutes)
```python
VALID_DOMAINS = ['amazon.com', 'amazon.co.uk', 'amazon.de', ...]

if values[CONF_URL] not in VALID_DOMAINS:
    raise ValueError(f"Invalid domain. Choose: {', '.join(VALID_DOMAINS)}")

if values.get(CONF_AUTH_SECRET):
    try:
        base64.b32decode(values[CONF_AUTH_SECRET])
    except Exception:
        raise ValueError("OTP secret must be valid base32")
```

### 2. Fix File Permissions (15 minutes)
```python
# alexa/__init__.py:211-213
cookie_dir = os.path.join(mass.storage_path, ".alexa")
await asyncio.to_thread(os.makedirs, cookie_dir, mode=0o700, exist_ok=True)

# alexa/__init__.py:223 (after saving)
os.chmod(login._cookiefile[0], 0o600)
```

### 3. Improve Error Messages (1 hour)
```python
# Replace generic error (line 132)
raise LoginFailed(
    "Authentication failed. Common causes:\n"
    "1. Incorrect email/password\n"
    "2. Wrong Amazon domain (check amazon.com vs amazon.co.uk)\n"
    "3. 2FA required but OTP secret not provided\n"
    "4. Amazon CAPTCHA (try manual login first)\n"
    f"Error details: {error}"
)
```

---

## 🔄 Migration Path (Pickle → Encrypted JSON)

### Step 1: Create Migration Script
```python
async def migrate_cookie_storage():
    """Migrate from pickle to encrypted JSON."""
    cookie_dir = Path(storage_path) / ".alexa"

    for pickle_file in cookie_dir.glob("*.pickle"):
        # Load old pickle (one last time)
        try:
            with open(pickle_file, 'rb') as f:
                cookie_jar = pickle.load(f)

            # Convert to JSON format
            cookies = [
                {'name': c.key, 'value': c.value, 'domain': c['domain']}
                for c in cookie_jar
            ]

            # Save encrypted
            username = pickle_file.stem.replace('alexa_media.', '')
            await secure_storage.save_cookies(username, cookies)

            # Backup old file
            pickle_file.rename(pickle_file.with_suffix('.pickle.bak'))

        except Exception as e:
            _LOGGER.error(f"Failed to migrate {pickle_file}: {e}")
```

### Step 2: Update save_cookie()
```python
async def save_cookie(login: AlexaLogin, username: str, mass: MusicAssistant):
    """Save cookies using secure storage (no pickle)."""
    storage = SecureCookieStorage(
        storage_path=Path(mass.storage_path) / ".alexa",
        master_key=await get_encryption_key(mass)
    )

    cookie_jar = login._session.cookie_jar
    cookies = [
        {'name': c.key, 'value': c.value, 'domain': c['domain'], ...}
        for c in cookie_jar
    ]

    await storage.save_cookies(username, cookies)
```

---

## 📊 Monitoring & Metrics

**Log What Matters**:
```python
# Auth lifecycle events
_LOGGER.info("Alexa auth started for %s", obfuscate_email(username))
_LOGGER.info("Alexa auth successful, cookies saved")
_LOGGER.warning("Alexa session expired for %s", obfuscate_email(username))
_LOGGER.error("Alexa auth failed: %s", error_type)

# Cookie operations
_LOGGER.debug("Loading cookies from %s", cookie_path)
_LOGGER.debug("Cookies loaded successfully, %d entries", len(cookies))
_LOGGER.warning("Cookie file permissions insecure: %o", file_mode)

# API operations
_LOGGER.debug("Alexa API call: %s(%s)", api_method, args)
_LOGGER.warning("Alexa API call failed, retrying (%d/%d)", attempt, max_retries)
```

**Metrics to Track**:
- Auth success rate (should be >95%)
- Average auth time (should be <30s)
- Token refresh failures (should be <5%)
- Cookie file permission violations (should be 0%)

---

## 🎓 Learning Resources

**Security**:
- OWASP Secure Coding: https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/
- Python Cryptography: https://cryptography.io/en/latest/
- File Permissions Guide: `man chmod`, `man umask`

**Pickle Vulnerability**:
- https://davidhamann.de/2020/04/05/exploiting-python-pickle/
- https://blog.nelhage.com/2011/03/exploiting-pickle/

**OAuth2 Best Practices**:
- https://oauth.net/2/
- https://tools.ietf.org/html/rfc6749

---

## 🆘 Emergency Procedures

### If Pickle RCE Discovered in Production
1. **Immediate**: Disable Alexa provider in all deployments
2. **Validate**: Check all cookie files for tampering: `md5sum *.pickle`
3. **Remediate**: Delete all cookie files, force re-auth
4. **Deploy**: Patched version with encrypted storage
5. **Notify**: Users to re-authenticate and change Amazon passwords

### If Credentials Leaked
1. **Rotate**: Force all users to re-authenticate
2. **Audit**: Check Amazon account activity for unauthorized access
3. **Harden**: Deploy encryption + permission fixes immediately
4. **Document**: Post-mortem analysis and prevention plan

---

## ✅ Definition of Done

**Security Fix Complete When**:
- [ ] Code review passed (2+ reviewers)
- [ ] All critical vulnerabilities resolved
- [ ] Unit tests added (>80% coverage)
- [ ] Integration tests passed
- [ ] Security audit passed (internal or external)
- [ ] Documentation updated (user guide + developer guide)
- [ ] Deployment plan reviewed
- [ ] Rollback plan documented

**User-Facing When**:
- [ ] Migration script tested on 10+ real accounts
- [ ] Error messages are clear and actionable
- [ ] Troubleshooting guide published
- [ ] Release notes include security warnings
- [ ] Support team trained on new auth flow

---

**Last Updated**: 2025-10-25
**Maintained By**: Music Assistant Security Team
**Questions?**: See `ALEXA_AUTH_ANALYSIS.md` for deep dive
