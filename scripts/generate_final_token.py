#!/usr/bin/env python3
"""Generate MusicKit token with your credentials"""

import jwt
from datetime import datetime, timedelta

# Your credentials
TEAM_ID = "K69Q4G43Q4"
KEY_ID = "67B66GRRLJ"
KEY_FILE = "AuthKey_67B66GRRLJ.p8"

print("\n" + "="*70)
print("         GENERATING YOUR MUSICKIT TOKEN")
print("="*70)
print(f"\nTeam ID: {TEAM_ID}")
print(f"Key ID: {KEY_ID}")
print(f"Key File: {KEY_FILE}")

# Read the private key
with open(KEY_FILE, 'r') as f:
    private_key = f.read()

# Generate token valid for 180 days
token = jwt.encode(
    {
        "iss": TEAM_ID,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=180)
    },
    private_key,
    algorithm="ES256",
    headers={"kid": KEY_ID}
)

# Handle different jwt versions
if isinstance(token, bytes):
    token = token.decode('utf-8')

exp_date = datetime.utcnow() + timedelta(days=180)

print(f"\n✅ TOKEN GENERATED SUCCESSFULLY!")
print(f"Valid until: {exp_date.strftime('%B %d, %Y')}")

print("\n" + "="*70)
print("YOUR TOKEN:")
print("="*70)
print(token)
print("="*70)

# Save token
token_file = f"musickit_token_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
with open(token_file, 'w') as f:
    f.write(token)

print(f"\n📄 Token saved to: {token_file}")

# Create direct apply command
print("\n🚀 TO FIX MUSIC ASSISTANT, RUN THIS COMMAND:")
print("="*70)
print(f'''
ssh root@haboxhill.local << 'EOFTOKEN'
TOKEN="{token}"
echo "Saving new token to Music Assistant..."
docker exec addon_d5369777_music_assistant sh -c "echo '$TOKEN' > /data/apple_token_override.txt"
echo "Patching provider to use new token..."
docker exec addon_d5369777_music_assistant python3 -c "
import os
provider_file = '/app/venv/lib/python3.13/site-packages/music_assistant/providers/apple_music/__init__.py'
with open(provider_file, 'r') as f:
    content = f.read()
if 'apple_token_override' not in content:
    import_line = 'from music_assistant.helpers.app_vars import app_var'
    new_import = import_line + '\\nimport os'
    content = content.replace(import_line, new_import)
    old_line = 'MUSIC_APP_TOKEN = app_var(8)'
    new_line = 'MUSIC_APP_TOKEN = app_var(8)\\nif os.path.exists(\\'/data/apple_token_override.txt\\'):\\n    with open(\\'/data/apple_token_override.txt\\') as f:\\n        MUSIC_APP_TOKEN = f.read().strip()'
    content = content.replace(old_line, new_line)
    with open(provider_file, 'w') as f:
        f.write(content)
    print('Provider patched!')
else:
    print('Provider already patched')
"
echo "Restarting Music Assistant..."
docker restart addon_d5369777_music_assistant
echo "Done! Apple Music should work now!"
EOFTOKEN
''')

print("\nYour token is valid for 180 days!")
print(f"Set a reminder for {(datetime.utcnow() + timedelta(days=170)).strftime('%B %Y')} to renew it.")