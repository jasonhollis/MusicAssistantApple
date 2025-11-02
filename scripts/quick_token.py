#!/usr/bin/env python3
"""Quick MusicKit token generator - no frills version"""

import jwt
from datetime import datetime, timedelta

# EDIT THESE WITH YOUR CREDENTIALS
TEAM_ID = "YOUR_TEAM_ID"  # 10 characters (e.g., "ABCD123456")
KEY_ID = "YOUR_KEY_ID"    # 10 characters (e.g., "XYZ9876543")

# Paste your .p8 private key content here (including BEGIN/END lines)
PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
PASTE_YOUR_PRIVATE_KEY_HERE
-----END PRIVATE KEY-----"""

# Generate token valid for 180 days
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

# Handle different jwt versions
if isinstance(token, bytes):
    token = token.decode('utf-8')

print("\n" + "="*70)
print("YOUR MUSICKIT TOKEN:")
print("="*70)
print(token)
print("="*70)

# Apply to Music Assistant
print("\nTo apply this token to Music Assistant, run:")
print(f"""
ssh root@haboxhill.local "docker exec addon_d5369777_music_assistant sh -c 'echo \\"{token}\\" > /data/apple_token_override.txt'"

ssh root@haboxhill.local "docker restart addon_d5369777_music_assistant"
""")