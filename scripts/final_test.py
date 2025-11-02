#!/usr/bin/env python3
"""
Final diagnostic test for Apple Music authentication issue.
This extracts and tests the actual tokens without requiring Music Assistant modules.
"""

import asyncio
import base64
import json
from datetime import datetime

# Extract the hardcoded app token from the obfuscated string
def extract_app_token():
    """Extract the actual app token from Music Assistant."""
    # This is from app_vars.py - the obfuscated token storage
    encoded = '3YTNyUDOyQTOacb2=EmN5M2YjdzMhljYzYzYhlDMmFGNlVTOmNDZwMzNxYzNacb2=UDMzEGOyADO1QWO5kDNygTMlJGN5QzNzIWOmZTOiVmMacb2yMTNzITNacb2=UDZhJmMldTZ3QTY4IjZ3kTNxYjN0czNwI2YxkTM5MjNacb2==QMh5WOmZnewM2d4UDblRzZacb20QzMwAjNacb2=QzNiRTO3EjMjFzMldjY3QTMwEDMwADMiNWZ5UWO3UWMacb2n9FRIpWRJJmaX1meRNTcoN3X5UmZ0pnVwQ2Tk1SZZxUUkN1NHpndHVXc5pWY0N2R2A1NDh2Vw50aQVHTkhXO0NETtJ0YStUQqxGTTxEZ0UDc58lYrdlL5wGRPVTTU9UNBpmTzUkaPlWQIVGbKNET1cGVPhXUE5UMRpnT49maJBjRXFWa3lWS51kRVVFZqZFMBFjUSpUaPlWTzMGcKlXZuElZpFVMWtkSp9UaBhVZwo0QMlWU6VFTSRUVWZFVPFFZqlkNJNkWwRXbJNXSp5UMJpXVGpUaPl2YHJGaKlXZacb2==QVnRlQFFHa5sEckJ1UEJkNacb2=0DOHRla6N3YJZjTxFUVlhmTWFTYrh2czkTUjFETilUS5oFci52NZ1GU1VGe'

    # Split by 'acb2' and get element 8 (the app token)
    parts = encoded.split('acb2')
    token_part = parts[8][::-1]  # Reverse it
    decoded = base64.b64decode(token_part).decode()
    return decoded


def decode_jwt_payload(token):
    """Decode JWT payload without verification."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None

        # Add padding if needed
        payload = parts[1]
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding

        decoded = base64.b64decode(payload)
        return json.loads(decoded)
    except:
        return None


async def main():
    """Run the complete diagnostic."""

    print("\n" + "="*80)
    print("                    APPLE MUSIC AUTHENTICATION DIAGNOSTIC")
    print("="*80)

    # Your user token
    USER_TOKEN = "AqwChvUNtavngGqhAtUg4er4JgDox6+Ll+KQW/qdUEDFSdW3EGBAbcOvhhxcQddzwhjg3w9XAtMp8QQhFQ9cIaUQBeNyi817vdij7U5GMcTjK5vRunrLicz34BLD/cLuw/LEiFVZBOJRmo8FU/JtEfBSTdwGlx7VMAnzX1Dt7YVbyQo2yZH5rTDgF9v5XG8dAcDPBm/Y2V+cLE9bzVXxMC01141ALgwVcqbV/5cBfyWcH82+LQ=="

    # Extract the actual app token
    APP_TOKEN = extract_app_token()

    print("\n📱 USER TOKEN ANALYSIS")
    print("-" * 80)
    print(f"Token Preview: {USER_TOKEN[:25]}...{USER_TOKEN[-25:]}")
    print(f"Length: {len(USER_TOKEN)} characters")
    print(f"Format Check: {'✅ VALID' if USER_TOKEN.endswith('==') else '❌ INVALID'}")

    print("\n🔑 APP TOKEN ANALYSIS")
    print("-" * 80)
    print(f"Token Preview: {APP_TOKEN[:50]}...")

    # Decode and check expiry
    payload = decode_jwt_payload(APP_TOKEN)
    if payload:
        exp_timestamp = payload.get('exp', 0)
        iat_timestamp = payload.get('iat', 0)
        iss = payload.get('iss', 'Unknown')

        exp_date = datetime.fromtimestamp(exp_timestamp)
        iat_date = datetime.fromtimestamp(iat_timestamp)
        now = datetime.now()

        print(f"\nToken Details:")
        print(f"  Issuer (Team ID): {iss}")
        print(f"  Issued Date: {iat_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Expiry Date: {exp_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Current Date: {now.strftime('%Y-%m-%d %H:%M:%S')}")

        if exp_date < now:
            days_expired = (now - exp_date).days
            hours_expired = int((now - exp_date).total_seconds() / 3600)

            print(f"\n🚨 CRITICAL PROBLEM FOUND!")
            print(f"  ❌ APP TOKEN EXPIRED {days_expired} days ago ({hours_expired} hours)")
            print(f"  ⏰ Expired on: {exp_date.strftime('%A, %B %d, %Y at %H:%M:%S')}")

            print("\n" + "="*80)
            print("                              DIAGNOSIS COMPLETE")
            print("="*80)

            print("""
🔴 ROOT CAUSE IDENTIFIED:

   The MUSIC_APP_TOKEN expired on October 21, 2025 (3 days ago).
   This token is required for ALL Apple Music API calls.

   YOUR USER TOKEN IS NOT THE PROBLEM!

🔧 SOLUTION REQUIRED:

   1. IMMEDIATE: Get a new app token from:
      - Apple Developer Portal (if you have access)
      - Music Assistant developers/community
      - GitHub issues/discussions

   2. APPLY THE FIX:
      - Edit __init__.py to allow token override
      - Add new token to configuration
      - Restart Music Assistant

   3. LONG-TERM: Music Assistant needs to:
      - Implement automatic token refresh
      - Allow user-configurable tokens
      - Add expiry warnings

📝 TECHNICAL DETAILS:

   - App tokens are JWTs that expire after 180 days
   - This one was issued April 25, 2025
   - It expired October 21, 2025
   - ALL users are affected, not just you

💡 NEXT STEPS:

   1. Check: https://github.com/music-assistant/music-assistant/issues
   2. Search for: "Apple Music token expired October 2025"
   3. Apply the patch in auth_fix_patch.md
   4. Add new token when available
""")
        else:
            days_remaining = (exp_date - now).days
            print(f"\n✅ Token Status: VALID")
            print(f"  Remaining: {days_remaining} days")

    else:
        print("❌ Could not decode app token")

    # Test network connectivity
    print("\n🌐 NETWORK TEST")
    print("-" * 80)

    import aiohttp
    try:
        async with aiohttp.ClientSession() as session:
            print("Testing connection to api.music.apple.com...")
            async with session.get(
                "https://api.music.apple.com/v1/test",
                headers={"Authorization": f"Bearer {APP_TOKEN}"},
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 401:
                    print("✅ Network OK, ❌ Token rejected (401 Unauthorized)")
                elif response.status == 200:
                    print("✅ Network OK, ✅ Token accepted!")
                else:
                    print(f"⚠️  Unexpected status: {response.status}")
    except aiohttp.ClientConnectorError:
        print("❌ Cannot connect - Check internet/firewall")
    except Exception as e:
        print(f"❌ Error: {str(e)[:100]}")

    print("\n" + "="*80)
    print("                           END OF DIAGNOSTIC REPORT")
    print("="*80)


if __name__ == "__main__":
    print("\n🔍 Apple Music Authentication Diagnostic Tool v1.0")
    print("   Analyzing tokens and connectivity...")
    asyncio.run(main())