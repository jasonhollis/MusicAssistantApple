#!/usr/bin/env python3
"""
Generate a new MusicKit token for Apple Music in Music Assistant.
For Apple Developers only - requires your private key from Apple Developer Portal.
"""

import jwt
import datetime
import sys
import json

def generate_token(team_id, key_id, private_key_path, days_valid=180):
    """
    Generate a MusicKit token valid for specified days.

    Args:
        team_id: Your 10-character Team ID from Apple Developer
        key_id: Your 10-character Key ID for MusicKit
        private_key_path: Path to your .p8 private key file
        days_valid: How many days the token should be valid (max 180)
    """

    # Read the private key
    try:
        with open(private_key_path, 'r') as key_file:
            private_key = key_file.read()
    except FileNotFoundError:
        print(f"❌ Error: Private key file not found: {private_key_path}")
        return None
    except Exception as e:
        print(f"❌ Error reading private key: {e}")
        return None

    # Create the token
    token_exp_time = datetime.datetime.utcnow() + datetime.timedelta(days=days_valid)

    headers = {
        "alg": "ES256",
        "kid": key_id
    }

    payload = {
        "iss": team_id,
        "iat": datetime.datetime.utcnow(),
        "exp": token_exp_time,
        "origin": ["*"]  # Allow all origins, or specify your domains
    }

    try:
        # Generate the JWT token
        token = jwt.encode(
            payload,
            private_key,
            algorithm="ES256",
            headers=headers
        )

        # Handle different jwt library versions
        if isinstance(token, bytes):
            token = token.decode('utf-8')

        return token

    except Exception as e:
        print(f"❌ Error generating token: {e}")
        print("\nMake sure you have PyJWT installed with cryptography support:")
        print("  pip install pyjwt[crypto]")
        return None


def main():
    print("\n" + "="*70)
    print("              MUSICKIT TOKEN GENERATOR FOR MUSIC ASSISTANT")
    print("="*70)

    print("\n📋 PREREQUISITES:")
    print("1. Apple Developer Account")
    print("2. MusicKit identifier and key from developer.apple.com")
    print("3. Your Team ID and Key ID")
    print("4. The .p8 private key file")

    print("\n" + "-"*70)
    print("🔍 HOW TO GET YOUR CREDENTIALS:\n")

    print("1. Go to https://developer.apple.com/account")
    print("2. Navigate to 'Certificates, Identifiers & Profiles'")
    print("3. Go to 'Keys' section")
    print("4. Create or find your MusicKit key")
    print("5. Note your:")
    print("   - Team ID: (10 characters, e.g., 'ABCDEF1234')")
    print("   - Key ID: (10 characters, shown next to key name)")
    print("6. Download the .p8 private key file (only downloadable once!)")

    print("\n" + "-"*70)
    print("📝 ENTER YOUR INFORMATION:\n")

    # Get input from user
    team_id = input("Enter your Team ID (10 characters): ").strip()
    if len(team_id) != 10:
        print(f"⚠️  Warning: Team ID should be 10 characters (got {len(team_id)})")

    key_id = input("Enter your Key ID (10 characters): ").strip()
    if len(key_id) != 10:
        print(f"⚠️  Warning: Key ID should be 10 characters (got {len(key_id)})")

    private_key_path = input("Enter path to your .p8 private key file: ").strip()

    # Remove quotes if user quoted the path
    private_key_path = private_key_path.strip('"').strip("'")

    # Ask for validity period
    print("\nHow many days should the token be valid?")
    print("(Maximum 180 days, recommended 180)")
    days_str = input("Days [180]: ").strip() or "180"

    try:
        days_valid = int(days_str)
        if days_valid > 180:
            print("⚠️  Maximum is 180 days, setting to 180")
            days_valid = 180
    except ValueError:
        print("⚠️  Invalid number, using 180 days")
        days_valid = 180

    print("\n" + "-"*70)
    print("🔧 GENERATING TOKEN...\n")

    # Generate the token
    token = generate_token(team_id, key_id, private_key_path, days_valid)

    if token:
        print("✅ TOKEN GENERATED SUCCESSFULLY!\n")

        # Decode to show expiry
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            exp_date = datetime.datetime.fromtimestamp(decoded['exp'])
            print(f"Token valid until: {exp_date.strftime('%B %d, %Y at %H:%M:%S UTC')}")
            print(f"Days valid: {days_valid}")
        except:
            pass

        print("\n" + "="*70)
        print("YOUR NEW MUSICKIT TOKEN:")
        print("="*70)
        print("\n" + token)
        print("\n" + "="*70)

        # Save to file
        output_file = f"musickit_token_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(output_file, 'w') as f:
            f.write(f"# MusicKit Token for Music Assistant\n")
            f.write(f"# Generated: {datetime.datetime.now()}\n")
            f.write(f"# Valid until: {exp_date}\n")
            f.write(f"# Team ID: {team_id}\n")
            f.write(f"# Key ID: {key_id}\n\n")
            f.write(token)

        print(f"\n📄 Token saved to: {output_file}")

        print("\n" + "="*70)
        print("🚀 NEXT STEPS TO FIX MUSIC ASSISTANT:")
        print("="*70)

        print("""
1. SSH into your Home Assistant:
   ssh root@haboxhill.local

2. Apply the token (I'll do this for you automatically if you want):
   - The token needs to be added as an override in Music Assistant
   - Or we can patch the provider directly

3. Restart Music Assistant

Would you like me to automatically apply this token to your Music Assistant?
(I can SSH in and update it for you)
""")

        # Also create a ready-to-run SSH command
        ssh_command_file = f"apply_token_command_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.sh"
        with open(ssh_command_file, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write("# Command to apply the token to Music Assistant\n")
            f.write(f"# Generated: {datetime.datetime.now()}\n\n")
            f.write(f'TOKEN="{token}"\n\n')
            f.write('echo "Applying new MusicKit token to Music Assistant..."\n')
            f.write('ssh root@haboxhill.local "docker exec addon_d5369777_music_assistant python3 -c \\"')
            f.write("import json\\n")
            f.write("config_path = '/data/settings.json'\\n")
            f.write("# Read config\\n")
            f.write("with open(config_path) as f: config = json.load(f)\\n")
            f.write("# Update token\\n")
            f.write("if 'providers' not in config: config['providers'] = {}\\n")
            f.write("if 'apple_music' not in config['providers']: config['providers']['apple_music'] = {}\\n")
            f.write(f"config['providers']['apple_music']['app_token_override'] = '{token}'\\n")
            f.write("# Write config\\n")
            f.write("with open(config_path, 'w') as f: json.dump(config, f, indent=2)\\n")
            f.write('print(\\'Token applied to config!\\')\\n')
            f.write('\\""\\n')
            f.write('echo "Restarting Music Assistant..."\\n')
            f.write('ssh root@haboxhill.local "docker restart addon_d5369777_music_assistant"\n')
            f.write('echo "Done! Music Assistant should now work with Apple Music!"\n')

        print(f"📝 Ready-to-run script saved to: {ssh_command_file}")
        print(f"   Run it with: bash {ssh_command_file}")

        return token

    else:
        print("\n❌ Failed to generate token")
        print("\nCommon issues:")
        print("1. Wrong Team ID or Key ID")
        print("2. Invalid private key file")
        print("3. Missing PyJWT with cryptography: pip install pyjwt[crypto]")
        return None


if __name__ == "__main__":
    # Check for PyJWT
    try:
        import jwt
    except ImportError:
        print("❌ PyJWT not installed!")
        print("\nInstall it with:")
        print("  pip install pyjwt[crypto]")
        print("\nor:")
        print("  pip3 install pyjwt[crypto]")
        sys.exit(1)

    main()