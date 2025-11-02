#!/usr/bin/env python3
"""
Debug script to investigate Apple Music playlist sync issues.

This script tests the Apple Music API directly to determine why playlists
are not being synced into Music Assistant.

Usage:
    python3 debug_apple_playlists.py
"""

import asyncio
import json
import sys
import os
from pathlib import Path

# Add the server path for imports
server_path = Path(__file__).parent / "server-2.6.0"
sys.path.insert(0, str(server_path))

import aiohttp


class AppleMusicPlaylistDebugger:
    """Debug Apple Music playlist API calls."""

    def __init__(self, music_app_token: str, music_user_token: str):
        """Initialize with tokens."""
        self.music_app_token = music_app_token
        self.music_user_token = music_user_token
        self.base_url = "https://api.music.apple.com/v1"

    async def get_storefront(self, session: aiohttp.ClientSession) -> str:
        """Get user's storefront."""
        url = f"{self.base_url}/me/storefront"
        headers = {
            "Authorization": f"Bearer {self.music_app_token}",
            "Music-User-Token": self.music_user_token,
        }

        print("\n" + "="*80)
        print("STEP 1: Getting user storefront...")
        print("="*80)

        async with session.get(url, headers=headers, ssl=True) as response:
            print(f"Status: {response.status}")
            print(f"Headers: {dict(response.headers)}")

            if response.status != 200:
                text = await response.text()
                print(f"Error response: {text}")
                raise Exception(f"Failed to get storefront: {response.status}")

            data = await response.json()
            print(f"Response data: {json.dumps(data, indent=2)}")

            storefront = data["data"][0]["id"]
            print(f"\n✓ Storefront: {storefront}")
            return storefront

    async def test_library_playlists_direct(self, session: aiohttp.ClientSession):
        """Test the me/library/playlists endpoint directly."""
        endpoint = "me/library/playlists"
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.music_app_token}",
            "Music-User-Token": self.music_user_token,
        }

        print("\n" + "="*80)
        print("STEP 2: Testing me/library/playlists endpoint (direct call)")
        print("="*80)
        print(f"URL: {url}")
        print(f"Headers: {headers}")

        async with session.get(url, headers=headers, ssl=True) as response:
            print(f"\nStatus: {response.status}")
            print(f"Response Headers: {dict(response.headers)}")

            if response.status != 200:
                text = await response.text()
                print(f"Error response: {text}")
                return None

            data = await response.json()
            print(f"\nResponse structure:")
            print(f"  - Keys: {list(data.keys())}")
            if "data" in data:
                print(f"  - Data length: {len(data['data'])}")
                print(f"\nFull response: {json.dumps(data, indent=2)}")

                if len(data['data']) > 0:
                    print(f"\n✓ Found {len(data['data'])} playlists!")
                    print("\nFirst playlist:")
                    print(json.dumps(data['data'][0], indent=2))
                else:
                    print("\n✗ API returned 0 playlists in 'data' array")
            else:
                print(f"\n✗ No 'data' key in response!")
                print(f"Full response: {json.dumps(data, indent=2)}")

            return data

    async def test_library_playlists_paginated(self, session: aiohttp.ClientSession):
        """Test the me/library/playlists endpoint with pagination parameters."""
        endpoint = "me/library/playlists"
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.music_app_token}",
            "Music-User-Token": self.music_user_token,
        }

        print("\n" + "="*80)
        print("STEP 3: Testing me/library/playlists with pagination (limit=50, offset=0)")
        print("="*80)

        params = {"limit": 50, "offset": 0}
        print(f"URL: {url}")
        print(f"Params: {params}")

        async with session.get(url, headers=headers, params=params, ssl=True) as response:
            print(f"\nStatus: {response.status}")

            if response.status == 404:
                print("✗ Got 404 - this might be why sync returns empty!")
                print("   The _get_all_items method returns {} when limit+offset get 404")
                return None

            if response.status != 200:
                text = await response.text()
                print(f"Error response: {text}")
                return None

            data = await response.json()
            print(f"\nResponse structure:")
            print(f"  - Keys: {list(data.keys())}")
            if "data" in data:
                print(f"  - Data length: {len(data['data'])}")
                if len(data['data']) > 0:
                    print(f"\n✓ Found {len(data['data'])} playlists with pagination!")
                else:
                    print("\n✗ Pagination returned 0 playlists")

            return data

    async def test_catalog_playlists(self, session: aiohttp.ClientSession, storefront: str):
        """Test catalog playlists (public/curated playlists)."""
        endpoint = f"catalog/{storefront}/playlists"
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.music_app_token}",
        }

        print("\n" + "="*80)
        print("STEP 4: Testing catalog playlists (for comparison)")
        print("="*80)
        print(f"URL: {url}")

        # Get a featured playlist as a test
        params = {"limit": 5}
        async with session.get(url, headers=headers, params=params, ssl=True) as response:
            print(f"Status: {response.status}")

            if response.status != 200:
                text = await response.text()
                print(f"Error: {text}")
                return None

            data = await response.json()
            print(f"\nCatalog playlists found: {len(data.get('data', []))}")
            if data.get('data'):
                print(f"Sample catalog playlist: {data['data'][0]['attributes']['name']}")

            return data

    async def simulate_get_all_items(self, session: aiohttp.ClientSession):
        """Simulate the _get_all_items method from the provider."""
        endpoint = "me/library/playlists"
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.music_app_token}",
            "Music-User-Token": self.music_user_token,
        }

        print("\n" + "="*80)
        print("STEP 5: Simulating _get_all_items pagination logic")
        print("="*80)
        print("This mimics what the Apple Music provider does internally...")

        limit = 50
        offset = 0
        all_items = []
        page = 0

        while True:
            page += 1
            params = {"limit": limit, "offset": offset}

            print(f"\n--- Page {page} (offset={offset}, limit={limit}) ---")

            async with session.get(url, headers=headers, params=params, ssl=True) as response:
                print(f"Status: {response.status}")

                # This is the critical check from _get_data
                if response.status == 404 and "limit" in params and "offset" in params:
                    print("✗ Got 404 with pagination params - returning empty dict")
                    print("   This is the bug! Method returns {} and breaks the loop")
                    break

                if response.status != 200:
                    text = await response.text()
                    print(f"Error: {text}")
                    break

                result = await response.json()

                if "data" not in result:
                    print("✗ No 'data' key - breaking")
                    break

                items_count = len(result["data"])
                print(f"Got {items_count} items")
                all_items.extend(result["data"])

                if not result.get("next"):
                    print("No 'next' pagination link - done")
                    break

                offset += limit

        print(f"\n{'='*80}")
        print(f"TOTAL ITEMS COLLECTED: {len(all_items)}")
        print(f"{'='*80}")

        return all_items

    async def run_all_tests(self):
        """Run all diagnostic tests."""
        print("\n" + "="*80)
        print("APPLE MUSIC PLAYLIST SYNC DEBUGGER")
        print("="*80)
        print(f"App Token: {self.music_app_token[:20]}...")
        print(f"User Token: {self.music_user_token[:20]}...")

        async with aiohttp.ClientSession() as session:
            try:
                # Get storefront
                storefront = await self.get_storefront(session)

                # Test direct API call
                await self.test_library_playlists_direct(session)

                # Test with pagination params
                await self.test_library_playlists_paginated(session)

                # Test catalog playlists for comparison
                await self.test_catalog_playlists(session, storefront)

                # Simulate the actual pagination logic
                items = await self.simulate_get_all_items(session)

                print("\n" + "="*80)
                print("DIAGNOSTIC SUMMARY")
                print("="*80)
                print(f"Total playlists found: {len(items)}")

                if len(items) == 0:
                    print("\n⚠️  PROBLEM IDENTIFIED:")
                    print("   - The API is returning 0 playlists")
                    print("   - This could mean:")
                    print("     1. Your Apple Music account has no playlists")
                    print("     2. The user token doesn't have playlist access")
                    print("     3. The API endpoint requires different parameters")
                    print("     4. There's an issue with the hasCatalog filtering")
                else:
                    print(f"\n✓ SUCCESS: Found {len(items)} playlists!")
                    print("\nPlaylist names:")
                    for idx, item in enumerate(items[:10], 1):
                        name = item.get("attributes", {}).get("name", "Unknown")
                        has_catalog = item.get("attributes", {}).get("hasCatalog", False)
                        can_edit = item.get("attributes", {}).get("canEdit", False)
                        print(f"  {idx}. {name} (hasCatalog={has_catalog}, canEdit={can_edit})")

                    if len(items) > 10:
                        print(f"  ... and {len(items) - 10} more")

            except Exception as e:
                print(f"\n✗ ERROR: {e}")
                import traceback
                traceback.print_exc()


async def main():
    """Main entry point."""
    # Load tokens from environment or config
    music_app_token = os.getenv("MUSIC_APP_TOKEN")
    music_user_token = os.getenv("MUSIC_USER_TOKEN")

    if not music_app_token or not music_user_token:
        print("ERROR: Missing tokens!")
        print("\nPlease set environment variables:")
        print("  export MUSIC_APP_TOKEN='your_app_token'")
        print("  export MUSIC_USER_TOKEN='your_user_token'")
        print("\nOr you can find them in the Music Assistant config:")
        print("  docker exec music-assistant cat /data/settings.json | jq '.providers.apple_music'")
        return 1

    debugger = AppleMusicPlaylistDebugger(music_app_token, music_user_token)
    await debugger.run_all_tests()

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
