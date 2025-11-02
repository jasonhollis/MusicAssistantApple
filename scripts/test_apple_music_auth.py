#!/usr/bin/env python3
"""
Test script for Apple Music authentication debugging.
Tests the provided Music User Token against Apple's API.
"""

import asyncio
import json
import re
import sys
from typing import Optional, Dict, Any
import aiohttp
from datetime import datetime, timedelta


class AppleMusicAuthTester:
    """Test Apple Music authentication tokens."""

    def __init__(self, user_token: str, app_token: Optional[str] = None):
        self.user_token = user_token
        self.app_token = app_token
        self.session: Optional[aiohttp.ClientSession] = None
        self.test_results = []

    async def setup(self):
        """Setup HTTP session."""
        self.session = aiohttp.ClientSession()

    async def cleanup(self):
        """Cleanup HTTP session."""
        if self.session:
            await self.session.close()

    def validate_token_format(self) -> bool:
        """Validate token format using the same regex as the provider."""
        if not isinstance(self.user_token, str):
            return False
        # This is the exact regex from line 126
        valid = re.findall(r"[a-zA-Z0-9=/+]{32,}==$", self.user_token)
        return bool(valid)

    async def test_storefront_api(self) -> Dict[str, Any]:
        """Test the first API call that happens during provider init (line 857)."""
        url = "https://api.music.apple.com/v1/me/storefront"
        headers = {
            "Authorization": f"Bearer {self.app_token}",
            "Music-User-Token": self.user_token,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            async with self.session.get(url, headers=headers, params={"l": "en"}, ssl=True, timeout=10) as response:
                response_data = {
                    "status": response.status,
                    "headers": dict(response.headers),
                    "url": str(response.url)
                }

                if response.status == 200:
                    data = await response.json()
                    response_data["data"] = data
                    response_data["storefront"] = data.get("data", [{}])[0].get("id", "Unknown")
                    response_data["success"] = True
                    response_data["message"] = f"Successfully retrieved storefront: {response_data['storefront']}"
                else:
                    try:
                        error_data = await response.text()
                        response_data["error"] = error_data
                    except:
                        response_data["error"] = "Could not read error response"

                    if response.status == 401:
                        response_data["message"] = "401 Unauthorized: Token is invalid or expired"
                    elif response.status == 403:
                        response_data["message"] = "403 Forbidden: Token doesn't match app token or access denied"
                    elif response.status == 429:
                        response_data["message"] = "429 Rate Limited: Too many requests"
                    else:
                        response_data["message"] = f"Unexpected status: {response.status}"
                    response_data["success"] = False

                return response_data

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Request failed: {e}",
                "status": None
            }

    async def test_app_token(self) -> Dict[str, Any]:
        """Test if the app token is valid (similar to line 132-141)."""
        if not self.app_token:
            return {
                "success": False,
                "message": "No app token provided",
                "status": None
            }

        url = "https://api.music.apple.com/v1/test"
        headers = {
            "Authorization": f"Bearer {self.app_token}"
        }

        try:
            async with self.session.get(url, headers=headers, ssl=True, timeout=10) as response:
                return {
                    "success": response.status == 200,
                    "status": response.status,
                    "message": "App token is valid" if response.status == 200 else f"App token invalid: {response.status}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"App token test failed: {e}",
                "status": None
            }

    async def test_library_artists(self) -> Dict[str, Any]:
        """Test access to library endpoint."""
        url = "https://api.music.apple.com/v1/me/library/artists"
        headers = {
            "Authorization": f"Bearer {self.app_token}",
            "Music-User-Token": self.user_token
        }

        try:
            async with self.session.get(url, headers=headers, params={"limit": 1}, ssl=True, timeout=10) as response:
                result = {
                    "status": response.status,
                    "success": response.status == 200
                }

                if response.status == 200:
                    data = await response.json()
                    result["message"] = f"Library access successful, found {len(data.get('data', []))} artists"
                else:
                    result["message"] = f"Library access failed: {response.status}"

                return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Library test failed: {e}",
                "status": None
            }

    def analyze_token(self) -> Dict[str, Any]:
        """Analyze token characteristics."""
        analysis = {
            "length": len(self.user_token),
            "format_valid": self.validate_token_format(),
            "ends_with_double_equals": self.user_token.endswith("=="),
            "is_base64": False,
            "character_set_valid": True
        }

        # Check if it's valid base64
        try:
            import base64
            base64.b64decode(self.user_token)
            analysis["is_base64"] = True
        except:
            analysis["is_base64"] = False

        # Check character set
        valid_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/=")
        token_chars = set(self.user_token)
        analysis["character_set_valid"] = token_chars.issubset(valid_chars)
        analysis["invalid_characters"] = list(token_chars - valid_chars)

        return analysis

    async def run_all_tests(self):
        """Run all authentication tests."""
        print("\n" + "="*60)
        print("APPLE MUSIC AUTHENTICATION TEST SUITE")
        print("="*60)

        # 1. Token Format Analysis
        print("\n1. TOKEN FORMAT ANALYSIS")
        print("-" * 40)
        analysis = self.analyze_token()
        print(f"   Token Length: {analysis['length']} characters")
        print(f"   Format Valid (regex): {analysis['format_valid']} ✓" if analysis['format_valid'] else f"   Format Valid (regex): {analysis['format_valid']} ✗")
        print(f"   Ends with '==': {analysis['ends_with_double_equals']} ✓" if analysis['ends_with_double_equals'] else f"   Ends with '==': {analysis['ends_with_double_equals']} ✗")
        print(f"   Valid Base64: {analysis['is_base64']}")
        print(f"   Character Set Valid: {analysis['character_set_valid']}")
        if analysis['invalid_characters']:
            print(f"   Invalid Characters: {analysis['invalid_characters']}")

        if not self.app_token:
            print("\n⚠️  WARNING: No app token provided. Some tests will be skipped.")
            print("   The app token is required for API calls.")
            return

        # 2. App Token Test
        print("\n2. APP TOKEN VALIDATION")
        print("-" * 40)
        app_result = await self.test_app_token()
        status_icon = "✓" if app_result['success'] else "✗"
        print(f"   Status: {app_result['status']} {status_icon}")
        print(f"   Result: {app_result['message']}")

        if not app_result['success']:
            print("\n⚠️  App token is invalid. Cannot proceed with user token tests.")
            return

        # 3. Storefront Test (Primary authentication test)
        print("\n3. USER TOKEN AUTHENTICATION (Storefront API)")
        print("-" * 40)
        storefront_result = await self.test_storefront_api()
        status_icon = "✓" if storefront_result['success'] else "✗"
        print(f"   Status: {storefront_result['status']} {status_icon}")
        print(f"   Result: {storefront_result['message']}")

        if storefront_result['success']:
            print(f"   Storefront ID: {storefront_result.get('storefront', 'Unknown')}")
        else:
            if storefront_result.get('error'):
                print(f"   Error Details: {storefront_result['error'][:200]}")

        # 4. Library Access Test
        if storefront_result['success']:
            print("\n4. LIBRARY ACCESS TEST")
            print("-" * 40)
            library_result = await self.test_library_artists()
            status_icon = "✓" if library_result['success'] else "✗"
            print(f"   Status: {library_result['status']} {status_icon}")
            print(f"   Result: {library_result['message']}")

        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)

        if storefront_result['success']:
            print("✅ Authentication SUCCESSFUL!")
            print("   Your token is valid and working.")
        else:
            print("❌ Authentication FAILED!")
            if storefront_result['status'] == 401:
                print("\nPossible causes:")
                print("   1. Token is expired (tokens expire after ~180 days)")
                print("   2. Token was revoked")
                print("   3. Token is invalid or corrupted")
                print("\nSolution: Re-authenticate through Music Assistant UI")
            elif storefront_result['status'] == 403:
                print("\nPossible causes:")
                print("   1. Token doesn't match the app token")
                print("   2. Token is from a different Apple ID")
                print("   3. Access forbidden for this resource")
                print("\nSolution: Ensure app token and user token are from same app")
            else:
                print(f"\nUnexpected error: {storefront_result.get('message', 'Unknown error')}")


async def main():
    """Main test runner."""

    # The user's token that isn't working
    USER_TOKEN = "AqwChvUNtavngGqhAtUg4er4JgDox6+Ll+KQW/qdUEDFSdW3EGBAbcOvhhxcQddzwhjg3w9XAtMp8QQhFQ9cIaUQBeNyi817vdij7U5GMcTjK5vRunrLicz34BLD/cLuw/LEiFVZBOJRmo8FU/JtEfBSTdwGlx7VMAnzX1Dt7YVbyQo2yZH5rTDgF9v5XG8dAcDPBm/Y2V+cLE9bzVXxMC01141ALgwVcqbV/5cBfyWcH82+LQ=="

    # You'll need to provide the app token - it should be in app_var(8) or MUSIC_APP_TOKEN
    # Check the Music Assistant logs or configuration for this value
    APP_TOKEN = None  # Replace with actual app token

    print("\n🔍 Testing Apple Music Authentication")
    print(f"   User Token: {USER_TOKEN[:20]}...{USER_TOKEN[-20:]}")
    print(f"   App Token: {'Not provided - some tests will be skipped' if not APP_TOKEN else f'{APP_TOKEN[:20]}...'}")

    tester = AppleMusicAuthTester(USER_TOKEN, APP_TOKEN)

    try:
        await tester.setup()
        await tester.run_all_tests()
    finally:
        await tester.cleanup()

    print("\n" + "="*60)
    print("DEBUGGING RECOMMENDATIONS")
    print("="*60)
    print("""
1. If you don't have the app token:
   - Check Music Assistant configuration for 'music_app_token'
   - Look in logs for 'Bearer' authentication headers
   - The app token is a JWT that starts with 'eyJ'

2. To manually test with curl:
   curl -v \\
     -H "Authorization: Bearer <app_token>" \\
     -H "Music-User-Token: <user_token>" \\
     https://api.music.apple.com/v1/me/storefront

3. Code fixes needed (based on analysis):
   - Add 401/403 error handling in _get_data() method
   - Add logging in handle_async_init()
   - Add try/except around _get_user_storefront() call
   - Implement token refresh mechanism

4. If token is expired:
   - Tokens expire after ~180 days
   - Re-authenticate through Music Assistant UI
   - Consider implementing automatic refresh
""")


if __name__ == "__main__":
    asyncio.run(main())