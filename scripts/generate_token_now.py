#!/usr/bin/env python3
"""Generate MusicKit token with your key file"""

import jwt
from datetime import datetime, timedelta
import sys

# Your Key ID (from filename)
KEY_ID = "67B66GRRLJ"

# Path to your key file
KEY_FILE = "AuthKey_67B66GRRLJ.p8"

print("\n" + "="*70)
print("         MUSICKIT TOKEN GENERATOR - READY TO GO!")
print("="*70)

print(f"\n✅ Found your key file: {KEY_FILE}")
print(f"✅ Key ID: {KEY_ID}")

# Get Team ID
print("\n📝 I just need your TEAM ID (10 characters)")
print("   You can find it at: https://developer.apple.com/account")
print("   Look in the 'Membership' section\n")

team_id = input("Enter your Team ID: ").strip()

if len(team_id) != 10:
    print(f"\n⚠️  Warning: Team ID should be 10 characters (you entered {len(team_id)})")
    confirm = input("Continue anyway? (y/n): ").lower()
    if confirm != 'y':
        print("Aborted.")
        sys.exit(1)

print("\n🔧 Generating token...")

try:
    # Read the private key
    with open(KEY_FILE, 'r') as f:
        private_key = f.read()

    # Generate token valid for 180 days
    token = jwt.encode(
        {
            "iss": team_id,
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

    # Calculate expiry
    exp_date = datetime.utcnow() + timedelta(days=180)

    print("\n" + "="*70)
    print("✅ TOKEN GENERATED SUCCESSFULLY!")
    print("="*70)

    print(f"\nToken valid until: {exp_date.strftime('%B %d, %Y')}")
    print("\nYOUR TOKEN:")
    print("-"*70)
    print(token)
    print("-"*70)

    # Save to file
    token_file = f"musickit_token_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(token_file, 'w') as f:
        f.write(f"# MusicKit Token for Music Assistant\n")
        f.write(f"# Generated: {datetime.now()}\n")
        f.write(f"# Valid until: {exp_date}\n")
        f.write(f"# Team ID: {team_id}\n")
        f.write(f"# Key ID: {KEY_ID}\n\n")
        f.write(token)
        f.write("\n")

    print(f"\n📄 Token saved to: {token_file}")

    # Create apply script
    apply_script = "apply_token_to_homeassistant.sh"
    with open(apply_script, 'w') as f:
        f.write("#!/bin/bash\n\n")
        f.write("# Apply MusicKit token to Music Assistant on Home Assistant\n")
        f.write(f"# Generated: {datetime.now()}\n\n")
        f.write(f'TOKEN="{token}"\n\n')
        f.write('echo "Connecting to Home Assistant..."\n')
        f.write('ssh root@haboxhill.local << \'EOF\'\n')
        f.write(f'TOKEN="{token}"\n')
        f.write('echo "Saving token to Music Assistant container..."\n')
        f.write('docker exec addon_d5369777_music_assistant sh -c "echo \\"$TOKEN\\" > /data/apple_token_override.txt"\n')
        f.write('echo "Token saved!"\n')
        f.write('echo "Patching provider to use override token..."\n')
        f.write('docker exec addon_d5369777_music_assistant python3 -c "\n')
        f.write('import os\n')
        f.write('provider_file = \\"/app/venv/lib/python3.13/site-packages/music_assistant/providers/apple_music/__init__.py\\"\n')
        f.write('with open(provider_file, \\'r\\') as f: content = f.read()\n')
        f.write('if \\"apple_token_override\\" not in content:\n')
        f.write('    # Add override logic after MUSIC_APP_TOKEN = app_var(8)\n')
        f.write('    content = content.replace(\n')
        f.write('        \\"MUSIC_APP_TOKEN = app_var(8)\\",\n')
        f.write('        \\"MUSIC_APP_TOKEN = app_var(8)\\\\n# Override with new token if available\\\\nif os.path.exists(\\'/data/apple_token_override.txt\\'):\\\\n    with open(\\'/data/apple_token_override.txt\\') as f:\\\\n        MUSIC_APP_TOKEN = f.read().strip()\\"\n')
        f.write('    )\n')
        f.write('    with open(provider_file, \\'w\\') as f: f.write(content)\n')
        f.write('    print(\\"Provider patched!\\")\\n')
        f.write('else:\\n')
        f.write('    print(\\"Provider already patched\\")\\n')
        f.write('"\n')
        f.write('echo "Restarting Music Assistant..."\n')
        f.write('docker restart addon_d5369777_music_assistant\n')
        f.write('echo "Waiting for container to start..."\n')
        f.write('sleep 10\n')
        f.write('echo "Checking logs for errors..."\n')
        f.write('docker logs --tail 50 addon_d5369777_music_assistant | grep -i "apple\\|music\\|token" || echo "No Apple Music entries in recent logs"\n')
        f.write('EOF\n\n')
        f.write('echo "\\n✅ Done! Music Assistant should now work with Apple Music!"\n')
        f.write('echo "Check the web UI and try to play an Apple Music track."\n')

    import os
    os.chmod(apply_script, 0o755)  # Make executable

    print(f"\n📝 Apply script created: {apply_script}")
    print("\n" + "="*70)
    print("🚀 APPLY TO HOME ASSISTANT NOW:")
    print("="*70)
    print(f"\nbash {apply_script}")
    print("\nOr if you prefer to do it manually:")
    print(f"""
ssh root@haboxhill.local
docker exec addon_d5369777_music_assistant sh -c 'echo "{token[:50]}..." > /data/apple_token_override.txt'
docker restart addon_d5369777_music_assistant
""")

    print("\n✅ Your token is valid for 180 days!")
    print(f"   Set a reminder for {(datetime.utcnow() + timedelta(days=170)).strftime('%B %Y')} to renew it.")

except FileNotFoundError:
    print(f"\n❌ Error: Could not find key file: {KEY_FILE}")
    print("   Make sure the file is in the current directory")
except Exception as e:
    print(f"\n❌ Error generating token: {e}")
    print("\nTroubleshooting:")
    print("1. Make sure PyJWT is installed: pip install pyjwt[crypto]")
    print("2. Check that the key file is valid")
    print("3. Verify your Team ID is correct")