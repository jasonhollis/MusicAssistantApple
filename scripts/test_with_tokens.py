#!/usr/bin/env python3
"""Test Apple Music authentication with extracted tokens."""

import asyncio
import base64
import aiohttp
import json
from datetime import datetime

# Extract the app token from the obfuscated data
def extract_app_token():
    """Extract app token from obfuscated string."""
    encoded = '3YTNyUDOyQTOacb2=EmN5M2YjdzMhljYzYzYhlDMmFGNlVTOmNDZwMzNxYzNacb2=UDMzEGOyADO1QWO5kDNygTMlJGN5QzNzIWOmZTOiVmMacb2yMTNzITNacb2=UDZhJmMldTZ3QTY4IjZ3kTNxYjN0czNwI2YxkTM5MjNacb2==QMh5WOmZnewM2d4UDblRzZacb20QzMwAjNacb2=QzNiRTO3EjMjFzMldjY3QTMwEDMwADMiNWZ5UWO3UWMacb2n9FRIpWRJJmaX1meRNTcoN3X5UmZ0pnVwQ2Tk1SZZxUUkN1NHpndHVXc5pWY0N2R2A1NDh2Vw50aQVHTkhXO0NETtJ0YStUQqxGTTxEZ0UDc58lYrdlL5wGRPVTTU9UNBpmTzUkaPlWQIVGbKNET1cGVPhXUE5UMRpnT49maJBjRXFWa3lWS51kRVVFZqZFMBFjUSpUaPlWTzMGcKlXZuElZpFVMWtkSp9UaBhVZwo0QMlWU6VFTSRUVWZFVPFFZqlkNJNkWwRXbJNXSp5UMJpXVGpUaPl2YHJGaKlXZacb2==QVnRlQFFHa5sEckJ1UEJkNacb2=0DOHRla6N3YJZjTxFUVlhmTWFTYrh2czkTUjFETilUS5oFci52NZ1GU1VGe'

    # Split by 'acb2' delimiter
    parts = encoded.split('acb2')

    # Get the 8th element (index 8) and reverse it
    if len(parts) > 8:
        token_part = parts[8][::-1]
        try:
            decoded = base64.b64decode(token_part).decode()
            return decoded
        except Exception as e:
            print(f"Error decoding token: {e}")
            return None
    return None


async def test_apple_music_auth():
    """Test Apple Music authentication with both tokens."""

    # User's token
    USER_TOKEN = "AqwChvUNtavngGqhAtUg4er4JgDox6+Ll+KQW/qdUEDFSdW3EGBAbcOvhhxcQddzwhjg3w9XAtMp8QQhFQ9cIaUQBeNyi817vdij7U5GMcTjK5vRunrLicz34BLD/cLuw/LEiFVZBOJRmo8FU/JtEfBSTdwGlx7VMAnzX1Dt7YVbyQo2yZH5rTDgF9v5XG8dAcDPBm/Y2V+cLE9bzVXxMC01141ALgwVcqbV/5cBfyWcH82+LQ=="

    # Extract app token
    APP_TOKEN = extract_app_token()

    if not APP_TOKEN:
        print("❌ Failed to extract app token")
        return

    print("\n" + "="*60)
    print("APPLE MUSIC AUTHENTICATION TEST")
    print("="*60)
    print(f"User Token: {USER_TOKEN[:20]}...{USER_TOKEN[-20:]}")
    print(f"App Token: {APP_TOKEN[:30]}...")

    # Parse JWT to check expiry
    try:
        # JWT structure: header.payload.signature
        parts = APP_TOKEN.split('.')
        if len(parts) == 3:
            # Decode payload (add padding if needed)
            payload = parts[1]
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            decoded_payload = base64.b64decode(payload)
            payload_json = json.loads(decoded_payload)

            # Check expiry
            if 'exp' in payload_json:
                exp_timestamp = payload_json['exp']
                exp_date = datetime.fromtimestamp(exp_timestamp)
                now = datetime.now()
                print(f"App Token Expires: {exp_date}")
                if exp_date < now:
                    print("⚠️  WARNING: App token is EXPIRED!")
                else:
                    days_left = (exp_date - now).days
                    print(f"✓ App token valid for {days_left} more days")
    except Exception as e:
        print(f"Could not parse JWT: {e}")

    print("\n" + "-"*60)
    print("TESTING AUTHENTICATION...")
    print("-"*60)

    async with aiohttp.ClientSession() as session:
        # Test 1: App Token
        print("\n1. Testing App Token...")
        try:
            async with session.get(
                "https://api.music.apple.com/v1/test",
                headers={"Authorization": f"Bearer {APP_TOKEN}"},
                ssl=True,
                timeout=10
            ) as response:
                if response.status == 200:
                    print("   ✅ App token is VALID")
                else:
                    print(f"   ❌ App token test failed: HTTP {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:200]}")
                    return
        except Exception as e:
            print(f"   ❌ App token test error: {e}")
            return

        # Test 2: User Token with Storefront API
        print("\n2. Testing User Token (Storefront API)...")
        try:
            headers = {
                "Authorization": f"Bearer {APP_TOKEN}",
                "Music-User-Token": USER_TOKEN,
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            async with session.get(
                "https://api.music.apple.com/v1/me/storefront",
                headers=headers,
                params={"l": "en"},
                ssl=True,
                timeout=10
            ) as response:
                print(f"   Response Status: {response.status}")

                if response.status == 200:
                    data = await response.json()
                    storefront = data.get("data", [{}])[0].get("id", "Unknown")
                    print(f"   ✅ Authentication SUCCESSFUL!")
                    print(f"   Storefront: {storefront}")

                    # Test library access
                    print("\n3. Testing Library Access...")
                    async with session.get(
                        "https://api.music.apple.com/v1/me/library/artists",
                        headers=headers,
                        params={"limit": 1},
                        ssl=True,
                        timeout=10
                    ) as lib_response:
                        if lib_response.status == 200:
                            lib_data = await lib_response.json()
                            artist_count = len(lib_data.get("data", []))
                            print(f"   ✅ Library access successful ({artist_count} artists)")
                        else:
                            print(f"   ⚠️  Library access failed: HTTP {lib_response.status}")

                elif response.status == 401:
                    print("   ❌ Authentication FAILED - Token is invalid or expired")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:300]}")
                    print("\n   SOLUTION: Token needs to be refreshed. Re-authenticate in Music Assistant.")

                elif response.status == 403:
                    print("   ❌ Access FORBIDDEN - Token doesn't match app token")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:300]}")
                    print("\n   SOLUTION: Tokens are mismatched. Re-authenticate with current app.")

                else:
                    print(f"   ❌ Unexpected error: HTTP {response.status}")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:300]}")

        except Exception as e:
            print(f"   ❌ Request failed: {e}")

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)


if __name__ == "__main__":
    print("Testing Apple Music Authentication...")
    asyncio.run(test_apple_music_auth())