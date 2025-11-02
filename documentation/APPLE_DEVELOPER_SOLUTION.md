# 🎉 SOLUTION: Generate Your Own MusicKit Token!

Since you're an Apple Developer, you can fix this immediately by generating your own MusicKit token!

## 📋 What You Need from Apple Developer Portal

1. **Go to**: https://developer.apple.com/account
2. **Navigate to**: Certificates, Identifiers & Profiles → Keys
3. **Find or Create**: A MusicKit key

You'll need:
- **Team ID**: 10-character ID (e.g., `ABCDEF1234`) - Found in Membership section
- **Key ID**: 10-character ID for your MusicKit key
- **Private Key**: The `.p8` file (downloadable only once when creating the key!)

## 🚀 Quick Method

### Option 1: Generate Token with Python Script

```bash
cd "/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple"

# Install PyJWT if needed
pip3 install pyjwt[crypto]

# Run the generator
python3 generate_musickit_token.py
```

The script will:
1. Ask for your Team ID, Key ID, and path to .p8 file
2. Generate a token valid for 180 days
3. Save it to a file
4. Create a script to apply it to Music Assistant

### Option 2: Quick Generation (if you have the credentials ready)

```python
import jwt
from datetime import datetime, timedelta

# Your credentials
TEAM_ID = "YOUR_TEAM_ID"  # 10 characters
KEY_ID = "YOUR_KEY_ID"    # 10 characters
PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
[Your private key content from .p8 file]
-----END PRIVATE KEY-----"""

# Generate token
token = jwt.encode(
    {
        "iss": TEAM_ID,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=180)
    },
    PRIVATE_KEY,
    algorithm="ES256",
    headers={"kid": KEY_ID}
)

print(token)
```

## 📝 Apply Token to Music Assistant

Once you have your token, I'll apply it to your Home Assistant:

### Method 1: Direct Patch (Immediate Fix)

```bash
# SSH into Home Assistant
ssh root@haboxhill.local

# Set your new token
NEW_TOKEN="YOUR_NEW_TOKEN_HERE"

# Apply directly to the provider
docker exec addon_d5369777_music_assistant python3 -c "
import os
# Create a simple override file
with open('/data/apple_token_override.txt', 'w') as f:
    f.write('$NEW_TOKEN')
print('Token saved!')
"

# Patch the provider to use it
docker exec addon_d5369777_music_assistant sed -i 's/MUSIC_APP_TOKEN = app_var(8)/# MUSIC_APP_TOKEN = app_var(8)  # Commented out - using override/' /app/venv/lib/python3.13/site-packages/music_assistant/providers/apple_music/__init__.py

docker exec addon_d5369777_music_assistant sed -i '/MUSIC_APP_TOKEN = app_var/a MUSIC_APP_TOKEN = open("/data/apple_token_override.txt").read().strip() if os.path.exists("/data/apple_token_override.txt") else app_var(8)' /app/venv/lib/python3.13/site-packages/music_assistant/providers/apple_music/__init__.py

# Restart Music Assistant
docker restart addon_d5369777_music_assistant
```

### Method 2: Configuration Override (Cleaner)

We can modify Music Assistant's configuration to accept an override token. This is cleaner but requires patching the provider code first.

## 🔍 Verify Your Token Works

Test your new token before applying:

```bash
# Test the token
curl -I -H "Authorization: Bearer YOUR_NEW_TOKEN_HERE" \
     https://api.music.apple.com/v1/test

# Should return: HTTP/2 200
```

## 🎯 Let Me Apply It For You!

**Just tell me when you have your token**, and I can:
1. SSH into your Home Assistant
2. Apply the token
3. Restart Music Assistant
4. Test that it works

Your token will be valid for 180 days (until April 2026), solving this problem for the next 6 months!

## 📌 Important Notes

- **Token Security**: Your token is semi-private - don't share it publicly
- **Validity**: Maximum 180 days per Apple's rules
- **Renewal**: Set a reminder for April 2026 to generate a new one
- **Your User Token**: Will continue working once the app token is fixed

## Need Help?

If you need help getting your credentials from Apple Developer Portal or generating the token, just let me know which step you're on!