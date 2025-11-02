# Apple Music Authentication Issue - SOLVED ✅

## Root Cause Identified

**THE APP TOKEN IS EXPIRED!** 🚨

- **App Token Expired**: October 21, 2025 (3 days ago)
- **Current Date**: October 24, 2025
- **Your User Token**: Valid format, but cannot work without valid app token

## Why Your Authentication Is Failing

1. **Primary Issue**: The MUSIC_APP_TOKEN (JWT) expired on 2025-10-21 07:59:49
2. **Secondary Issue**: Network connectivity error (possibly due to expired token rejection)
3. **Your User Token**: Format is correct, but it cannot authenticate without a valid app token

The authentication chain requires BOTH tokens:
- App Token (JWT) - Authenticates the application with Apple
- User Token - Authenticates the user's Apple Music account

When the app token expires, NO user tokens will work, regardless of their validity.

## Immediate Solution

### Option 1: Get New App Token (Recommended)

The app token needs to be regenerated. This is a JWT that must be created using:

1. **Apple Developer Account** with MusicKit enabled
2. **Private key** from Apple Developer portal
3. **Team ID** and **Key ID** from your MusicKit configuration

To generate a new token:

```python
import jwt
import datetime

# You need these from Apple Developer Portal
TEAM_ID = "YOUR_TEAM_ID"
KEY_ID = "YOUR_KEY_ID"
PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
YOUR_PRIVATE_KEY_HERE
-----END PRIVATE KEY-----"""

# Generate token (valid for 180 days)
token = jwt.encode(
    {
        "iss": TEAM_ID,
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=180),
        "origin": ["*"]  # Or specific domains
    },
    PRIVATE_KEY,
    algorithm="ES256",
    headers={
        "alg": "ES256",
        "kid": KEY_ID
    }
)
```

### Option 2: Update Music Assistant

Check if there's a newer version of Music Assistant with an updated token:

```bash
# Check for updates
cd "/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple"
git pull  # If it's a git repository
```

### Option 3: Manually Replace Token

If you can obtain a new valid app token from the Music Assistant community or developers:

1. Edit the obfuscated token in `app_vars.py`
2. OR override it in the provider configuration
3. OR patch the provider to use a config value instead

## Code Fixes Needed

### 1. Add App Token Configuration (Priority: CRITICAL)

```python
# In get_config_entries() function, add:
ConfigEntry(
    key="music_app_token_override",
    type=ConfigEntryType.SECURE_STRING,
    label="Override App Token (Advanced)",
    description="Override the built-in app token if expired. Get from Apple Developer Portal.",
    required=False,
    hidden=False,  # Make visible when default token is expired
    value=values.get("music_app_token_override") if values else None,
)
```

### 2. Check Token Expiry on Init

```python
# In handle_async_init(), add:
import jwt
import datetime

# Check if app token is expired
try:
    decoded = jwt.decode(self._music_app_token, options={"verify_signature": False})
    exp_date = datetime.datetime.fromtimestamp(decoded['exp'])
    if exp_date < datetime.datetime.now():
        self.logger.error(
            "App token expired on %s. Please update Music Assistant or provide new token.",
            exp_date
        )
        raise LoginFailed(f"App token expired on {exp_date}. Cannot authenticate.")
except jwt.DecodeError:
    self.logger.warning("Could not decode app token to check expiry")
```

### 3. Better Error Messages

The current error handling doesn't distinguish between:
- Expired app token (affects ALL users)
- Invalid user token (affects one user)
- Network issues

## Testing Your Fix

Once you have a new app token:

```bash
# Test with the new token
curl -H "Authorization: Bearer NEW_APP_TOKEN_HERE" \
     https://api.music.apple.com/v1/test

# If that works, test your user token:
curl -H "Authorization: Bearer NEW_APP_TOKEN_HERE" \
     -H "Music-User-Token: YOUR_USER_TOKEN" \
     https://api.music.apple.com/v1/me/storefront
```

## Long-term Solution

As mentioned in the TODO comments in the code:

1. **Implement token refresh mechanism**:
   - GitHub Action to generate new token weekly
   - Download fresh token on provider init
   - Store in cache with expiry check

2. **Make token configurable**:
   - Allow users to provide their own app token
   - Useful for development and when default expires

3. **Add token monitoring**:
   - Log warning 30 days before expiry
   - Show in UI when token will expire
   - Prompt for update before expiry

## Summary

**Your user token is likely fine** - the problem is the expired app token that affects ALL Music Assistant Apple Music users. The app token expired 3 days ago (October 21, 2025).

**Immediate action**: Obtain a new app token either by:
1. Generating one with Apple Developer account
2. Getting updated token from Music Assistant developers
3. Updating to newer Music Assistant version (if available)

**Error in provider**: No error handling for expired app tokens - it fails silently making debugging difficult.

---

## Quick Commands

```bash
# Check if you can reach Apple Music API
ping api.music.apple.com

# Test current app token (will fail - it's expired)
curl -I -H "Authorization: Bearer eyJhbGciOiJFUzI1NiIsImtpZCI6IjdQOTVVUDRLUzQiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJTNDQ2MzY5WDVNIiwiZXhwIjoxNzYxMDU0Nzg5LCJpYXQiOjE3NDUyNDYzODl9.W_pgDF0TqKvzMlFp8iWaLZMZYHZ-7uPnFNG1hRvNb8nNhkceJxZfqaMWtocJmMqoNaOFjRtCQZRTPI7W2BnVDg" \
     https://api.music.apple.com/v1/test

# Once you have new token, test it
curl -I -H "Authorization: Bearer NEW_TOKEN_HERE" \
     https://api.music.apple.com/v1/test
```