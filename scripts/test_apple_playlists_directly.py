#!/usr/bin/env python3
"""Test Apple Music playlist API directly to see what's returned"""

import aiohttp
import asyncio
import json

# Your tokens
APP_TOKEN = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjY3QjY2R1JSTEoiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJLNjlRNEc0M1E0IiwiaWF0IjoxNzYxMzA1MTc5LCJleHAiOjE3NzY4NTcxNzl9.hB2ORhgf2oC4HnMNjqEpPEFAeKSNqsajLAuinQUmWvxnkGrrsQbq0973AHe-HP5yNcb-YbLyEhN77jYYPGPfKA"
USER_TOKEN = "AqwChvUNtavngGqhAtUg4er4JgDox6+Ll+KQW/qdUEDFSdW3EGBAbcOvhhxcQddzwhjg3w9XAtMp8QQhFQ9cIaUQBeNyi817vdij7U5GMcTjK5vRunrLicz34BLD/cLuw/LEiFVZBOJRmo8FU/JtEfBSTdwGlx7VMAnzX1Dt7YVbyQo2yZH5rTDgF9v5XG8dAcDPBm/Y2V+cLE9bzVXxMC01141ALgwVcqbV/5cBfyWcH82+LQ=="

async def test_playlists():
    """Test playlist API directly"""

    print("🎵 Testing Apple Music Playlist API")
    print("="*60)

    endpoint = "https://api.music.apple.com/v1/me/library/playlists"
    headers = {
        "Authorization": f"Bearer {APP_TOKEN}",
        "Music-User-Token": USER_TOKEN
    }

    async with aiohttp.ClientSession() as session:
        # Test with different parameters
        tests = [
            {"limit": 50, "offset": 0},  # First page
            {"limit": 50},  # No offset
            {},  # No params
        ]

        for params in tests:
            print(f"\n📋 Testing with params: {params}")
            try:
                async with session.get(endpoint, headers=headers, params=params) as response:
                    print(f"  Status: {response.status}")

                    if response.status == 200:
                        data = await response.json()
                        playlists = data.get("data", [])
                        print(f"  ✅ Found {len(playlists)} playlists")

                        if playlists:
                            for i, playlist in enumerate(playlists[:3]):
                                attrs = playlist.get("attributes", {})
                                name = attrs.get("name", "Unknown")
                                print(f"    {i+1}. {name}")
                            if len(playlists) > 3:
                                print(f"    ... and {len(playlists)-3} more")

                        # Check for next page
                        if "next" in data:
                            print(f"  ℹ️ Has more pages: {data['next']}")

                    elif response.status == 404:
                        print(f"  ❌ 404 Not Found")
                        text = await response.text()
                        print(f"  Response: {text[:200]}")

                    else:
                        print(f"  ❌ Error: {response.status}")

            except Exception as e:
                print(f"  ❌ Exception: {e}")

    print("\n" + "="*60)
    print("SUMMARY:")
    print("If you see playlists above, the API works and the bug is in Music Assistant")
    print("If you see 404 errors, there might be a token or API issue")

if __name__ == "__main__":
    asyncio.run(test_playlists())