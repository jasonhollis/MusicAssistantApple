# Alexa Authentication Troubleshooting Guide
**Category**: Operations & Maintenance
**Date**: 2025-10-25
**Status**: Active
**Related Architecture**: See `../00_ARCHITECTURE/ALEXA_AUTHENTICATION_STRATEGIC_ANALYSIS.md`

---

## Quick Diagnosis

### Symptom: "Authentication Failed" or "Login Error Detected"

**Most Common Causes** (in order of likelihood):

1. **Passkeys enabled on Amazon account** → See [Passkey Conflict Resolution](#passkey-conflict-resolution)
2. **Wrong 2FA method** → See [2FA Configuration](#2fa-configuration)
3. **Expired cookies** → See [Cookie Refresh](#cookie-refresh)
4. **Amazon captcha challenge** → See [Captcha Issues](#captcha-issues)
5. **Account security lockout** → See [Account Lockout](#account-lockout)

---

## Passkey Conflict Resolution

### Problem: Passkeys Prevent Third-Party Authentication

**How to Identify**:
```bash
# Check if your Amazon account has passkeys enabled:
# 1. Go to: https://www.amazon.com/gp/security/view-security-settings
# 2. Look for "Passkeys and security keys" section
# 3. If you see any passkeys listed, this is your issue
```

**Why This Happens**:
Amazon's passkey implementation doesn't support third-party OAuth2 flows. When passkeys are enabled, cookie-based authentication fails.

**Solutions** (choose one):

#### Option A: Use Authenticator App 2FA (Recommended)

**DO NOT disable passkeys!** Instead, set up authenticator app for third-party integrations:

**Step-by-Step**:

1. **Go to Amazon 2FA Settings**:
   ```
   https://www.amazon.com/a/settings/approval
   ```

2. **Add Authenticator App**:
   - Click "Add new phone or authenticator app"
   - Select "Authenticator App"
   - Click "Can't scan the barcode?"

3. **Extract the Seed**:
   - Copy the **52-character bolded value** (looks like: `ABCD EFGH IJKL MNOP QRST UVWX YZ23 4567 8ABC DEFG HIJK LMNO`)
   - Remove spaces: `ABCDEFGHIJKLMNOPQRSTUVWXYZ234567890ABCDEFGHIJKLMNO`

4. **Add to Your Authenticator App**:
   - Google Authenticator: Manual entry
   - Authy: Add account → Enter key manually
   - 1Password: New item → One-Time Password → Paste key

5. **Configure Music Assistant**:
   ```yaml
   # In Music Assistant Alexa config:
   amazon_email: your.email@example.com
   amazon_password: your_password
   amazon_2fa_key: ABCDEFGHIJKLMNOPQRSTUVWXYZ234567890ABCDEFGHIJKLMNO
   ```

6. **Test Authentication**:
   - Music Assistant will now generate TOTP codes automatically
   - You keep using passkeys for normal Amazon login
   - Third-party apps use password + TOTP

**Security Warning**:
⚠️ The 52-character key allows unlimited 2FA code generation. Anyone with this key can bypass your 2FA. Store securely!

#### Option B: Disable Passkeys (Not Recommended)

**Only if Option A doesn't work**:

1. Go to: https://www.amazon.com/gp/security/view-security-settings
2. Find "Passkeys and security keys" section
3. Remove all passkeys
4. Revert to traditional password + 2FA

**Downside**: You lose the convenience of passkey login for regular Amazon use.

---

## 2FA Configuration

### Problem: Wrong 2FA Method Configured

**Supported 2FA Methods for Third-Party Integration**:
- ✅ **Authenticator App** (TOTP) - **BEST**
- ❌ **SMS Text Message** - Does not work with automation
- ❌ **Passkeys** - Not supported for third-party apps
- ❌ **Email OTP** - Does not work with automation

**How to Switch to Authenticator App**:

1. **Check Current 2FA Method**:
   - Go to: https://www.amazon.com/a/settings/approval
   - Look at "Two-Step Verification (2SV) Settings"

2. **If Using SMS**:
   - Click "Add new phone or authenticator app"
   - Choose "Authenticator App"
   - Follow setup process (see [Passkey Conflict Resolution](#passkey-conflict-resolution) for detailed steps)
   - **Optional**: Remove SMS method after authenticator app is working

3. **Verify Configuration**:
   ```bash
   # Test TOTP code generation:
   # Using Python (if you have pyotp installed):
   python3 -c "import pyotp; print(pyotp.TOTP('YOUR_52_CHAR_KEY').now())"

   # This should output a 6-digit code that matches your authenticator app
   ```

---

## Cookie Refresh

### Problem: Cookies Expired (14-day lifetime)

**Symptoms**:
- Authentication worked before, stopped suddenly
- "Session expired" or "Please login again" messages
- Happened ~2 weeks since last successful auth

**Manual Cookie Refresh**:

```bash
# Using alexa-cookie library (Node.js example):
node refresh_cookies.js

# Using Python (if using custom implementation):
python3 refresh_alexa_cookies.py
```

**Automatic Refresh Configuration**:

```yaml
# In Music Assistant config (example):
alexa:
  cookie_refresh:
    enabled: true
    interval_days: 7  # Refresh every 7 days (well before 14-day expiry)
    notify_on_failure: true
```

**Best Practices**:
- Refresh every 5-7 days (not waiting until day 14)
- Store `formerRegistrationData` to avoid creating duplicate devices
- Log cookie age for monitoring

**Monitoring Script**:

```python
import time
import json

# Check cookie age
with open('alexa_cookies.json', 'r') as f:
    cookie_data = json.load(f)

cookie_timestamp = cookie_data.get('timestamp', 0)
cookie_age_days = (time.time() - cookie_timestamp) / (24 * 60 * 60)

if cookie_age_days > 7:
    print(f"⚠️ Cookies are {cookie_age_days:.1f} days old - refresh recommended")
elif cookie_age_days > 12:
    print(f"🚨 Cookies are {cookie_age_days:.1f} days old - URGENT: refresh now!")
else:
    print(f"✅ Cookies are {cookie_age_days:.1f} days old - OK")
```

---

## Captcha Issues

### Problem: Amazon Serving Captcha During Authentication

**Why This Happens**:
- Amazon detects automated/suspicious login attempts
- Too many failed authentication attempts
- Login from new IP address or location
- Headless browser detection

**Solutions**:

#### Option 1: Force Captcha to Appear

**If captcha doesn't show**:
1. Enter anything (e.g., `123456`) in the CAPTCHA field
2. Submit
3. Amazon will show the actual CAPTCHA
4. Solve and submit

#### Option 2: Use Clean Browser

**If stuck in captcha loop**:
1. Open **incognito/private browser window**
2. Navigate to Music Assistant configuration page
3. Complete authentication in clean browser session
4. This often works first try

#### Option 3: Delete Expired Pickle Files

**If using Python-based integration**:
```bash
# Find and delete expired pickle files:
find ~/.config/music-assistant -name "*.pickle" -mtime +14 -delete

# Or manually:
rm ~/.config/music-assistant/alexa/*.pickle
```

**Restart Music Assistant** after deleting pickle files.

#### Option 4: Reduce Authentication Frequency

**Prevent captcha triggers**:
- Don't retry failed auth immediately (wait 5+ minutes)
- Implement exponential backoff on failures
- Reduce cookie refresh frequency (but not below 5 days)
- Use consistent user-agent header

**Example Backoff Logic**:
```python
import time

retry_delays = [60, 300, 900, 3600]  # 1min, 5min, 15min, 1hr

for attempt, delay in enumerate(retry_delays):
    try:
        authenticate()
        break
    except CaptchaRequired:
        if attempt < len(retry_delays) - 1:
            print(f"Captcha required, waiting {delay}s before retry...")
            time.sleep(delay)
        else:
            raise
```

---

## Account Lockout

### Problem: Amazon Flagged Account for Suspicious Activity

**Symptoms**:
- "We detected unusual activity on your account"
- Account temporarily locked
- Requires password reset or security challenge

**Resolution**:

1. **Check Email**:
   - Look for security alerts from Amazon
   - Follow any unlock/verification links

2. **Verify Account Status**:
   - Try logging in via normal Amazon website
   - Complete any security challenges

3. **Wait Before Retry**:
   - If account is locked, wait 24-48 hours
   - Amazon may auto-unlock after cool-down period

4. **Contact Amazon Support**:
   - If locked for >48 hours, contact support
   - Do NOT mention third-party automation (say "trouble logging in")

**Prevention**:
- Use realistic user-agent headers (mimic official app)
- Implement rate limiting (max 1 req/sec)
- Don't refresh cookies more than once per day
- Use same IP address consistently if possible

---

## Reauthentication Loop

### Problem: Continuous Requests to Re-login

**Symptoms**:
- Asked to login every few hours or days
- Previously working authentication stops repeatedly
- "Authentication required" notifications

**Causes & Fixes**:

#### Cause 1: Not Storing `formerRegistrationData`

**Fix**:
```javascript
// When using alexa-cookie library:
const options = {
  formerRegistrationData: previousRegistrationData  // Must persist this!
};

const cookies = await alexaCookie.generateAlexaCookie(email, password, options);

// Save for next time:
saveToFile('registration_data.json', cookies.formerRegistrationData);
```

**Why**: Without this, each auth creates a new "device" at Amazon, triggering security flags.

#### Cause 2: Cookie Storage Issues

**Fix**:
```bash
# Check cookie file permissions:
ls -la ~/.config/music-assistant/alexa/cookies.json

# Should be:
# -rw------- (600) - only owner can read/write

# Fix permissions if needed:
chmod 600 ~/.config/music-assistant/alexa/cookies.json
```

#### Cause 3: Automatic Refresh Disabled

**Fix**:
```yaml
# Enable automatic cookie refresh:
alexa:
  cookie_refresh:
    enabled: true  # Must be true!
```

#### Cause 4: System Clock Drift

**Fix**:
```bash
# Check system time:
date

# If incorrect, sync time:
# macOS:
sudo sntp -sS time.apple.com

# Linux:
sudo ntpdate -s time.nist.gov

# Check timezone:
timedatectl  # Linux
# Or
date  # macOS (shows timezone)
```

**Why**: TOTP codes are time-based; clock drift causes authentication failures.

---

## Headless Browser Detection

### Problem: Amazon Blocking Automated Browser Sessions

**Symptoms**:
- Authentication works in manual browser, fails in headless
- "Please enable JavaScript" or similar messages
- Infinite redirects during login

**Solution**: **Don't use headless browsers for Amazon auth** ❌

**Why This Won't Work**:
- Amazon uses sophisticated fingerprinting (fingerprint.js)
- Detects headless mode even with stealth plugins
- Not worth the effort - use cookie-based or official OAuth2

**If You Must Try** (not recommended):
```javascript
// Puppeteer with stealth mode:
const puppeteer = require('puppeteer-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
puppeteer.use(StealthPlugin());

const browser = await puppeteer.launch({
  headless: false,  // Use headed mode (still may be detected)
  args: ['--disable-blink-features=AutomationControlled']
});
```

**Better Alternative**: Use `alexa-cookie` library which mimics mobile app (not browser).

---

## Error Message Reference

### Common Error Messages & Solutions

| Error Message | Cause | Solution |
|--------------|-------|----------|
| "Login error detected; not contacting API" | Cookie expired or invalid | [Cookie Refresh](#cookie-refresh) |
| "Invalid 2FA key" | Wrong TOTP seed or clock drift | Verify 52-char key, check system time |
| "Captcha required" | Too many auth attempts | [Captcha Issues](#captcha-issues) |
| "Authentication required" (continuous) | Not storing formerRegistrationData | [Reauthentication Loop](#reauthentication-loop) |
| "Invalid Built-In 2FA key" | Incorrect seed format | Re-extract seed, remove spaces |
| "Session expired" | Cookies older than 14 days | [Cookie Refresh](#cookie-refresh) |
| "Please enable JavaScript" | Headless browser detected | Don't use headless browsers |
| "Account locked" | Amazon security flag | [Account Lockout](#account-lockout) |

---

## Diagnostic Commands

### Check Authentication Status

```bash
# View current cookie age:
find ~/.config/music-assistant -name "cookies.json" -exec stat -f "%Sm %N" {} \;

# Test TOTP generation:
python3 -c "import pyotp; print(pyotp.TOTP('YOUR_KEY').now())"

# Check stored credentials (careful - sensitive!):
cat ~/.config/music-assistant/alexa/config.json | jq '.credentials'

# View authentication logs:
tail -f ~/.config/music-assistant/logs/alexa_auth.log
```

### Test Connection

```bash
# Using alexa-cookie library:
node test_auth.js

# Using Music Assistant CLI (if available):
music-assistant alexa test-auth

# Manual API test:
curl -H "Cookie: $(cat cookies.txt)" \
     https://alexa.amazon.com/api/bootstrap
```

---

## When All Else Fails

### Nuclear Option: Complete Re-Authentication

**Steps**:

1. **Remove All Stored Data**:
   ```bash
   # Backup first!
   cp -r ~/.config/music-assistant/alexa ~/.config/music-assistant/alexa.backup

   # Remove all authentication data:
   rm -rf ~/.config/music-assistant/alexa/*
   ```

2. **Delete Amazon Devices** (optional):
   - Go to: https://www.amazon.com/gp/css/homepage.html
   - Click "Content & Devices" → "Devices"
   - Remove any "Music Assistant" or unknown devices

3. **Reconfigure from Scratch**:
   - Follow initial setup guide
   - Use fresh authenticator app seed
   - Don't reuse old pickle/cookie files

4. **Monitor First 48 Hours**:
   - Check authentication stays stable
   - Watch for immediate reauthentication requests
   - If issues recur immediately, likely passkey or 2FA method problem

---

## Preventive Maintenance

### Regular Checks (Monthly)

- [ ] Verify automatic cookie refresh is working
- [ ] Check cookie age doesn't exceed 12 days
- [ ] Review authentication logs for errors
- [ ] Test authentication still works
- [ ] Update alexa-cookie library (check for updates)

### Configuration Health Check

```bash
# Run this monthly:

# 1. Check cookie age
find ~/.config/music-assistant -name "cookies.json" -mtime +12 && echo "⚠️ Cookies old!"

# 2. Verify TOTP works
python3 -c "import pyotp; code=pyotp.TOTP('YOUR_KEY').now(); print(f'TOTP: {code}')"

# 3. Check file permissions
find ~/.config/music-assistant/alexa -type f -not -perm 600 -ls

# 4. Verify formerRegistrationData exists
grep -q "formerRegistrationData" ~/.config/music-assistant/alexa/registration.json && echo "✅ OK"
```

---

## Getting Help

### Before Asking for Help

**Gather This Information**:

1. **Error messages** (exact text, not paraphrased)
2. **Authentication method** (cookie-based or Alexa Skill?)
3. **2FA method** (SMS, authenticator app, passkeys?)
4. **When it last worked** (if ever)
5. **Recent changes** (Amazon password change, enabled passkeys, etc.)
6. **Logs** (sanitize sensitive info!)

### Where to Get Help

- **Music Assistant GitHub Issues**: https://github.com/music-assistant/
- **Home Assistant Community**: https://community.home-assistant.io/
- **Reddit /r/homeassistant**: For general home automation help

### What NOT to Share Publicly

❌ Amazon email/password
❌ 52-character TOTP seed
❌ Cookie files
❌ Access tokens or refresh tokens
❌ Full configuration files (may contain secrets)

✅ Error messages (sanitized)
✅ Steps to reproduce
✅ System configuration (OS, versions)
✅ Authentication method (high-level)

---

## Document Metadata

**Last Updated**: 2025-10-25
**Applies To**: Cookie-based Alexa authentication (unofficial method)
**Does NOT Apply To**: Official Alexa Skill with OAuth2 (different troubleshooting)
**Review Frequency**: Monthly (Amazon changes fast)

**Related Documents**:
- Architecture: `../00_ARCHITECTURE/ALEXA_AUTHENTICATION_STRATEGIC_ANALYSIS.md`
- Setup Guide: `./ALEXA_SETUP_GUIDE.md` (if exists)

---

**END OF TROUBLESHOOTING GUIDE**
