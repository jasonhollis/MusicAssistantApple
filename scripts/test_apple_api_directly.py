#!/usr/bin/env python3
"""
Test Apple Music API directly to see what streams are available for spatial audio tracks
"""

import aiohttp
import asyncio
import json

# Your tokens
APP_TOKEN = "eyJhbGciOiJFUzI1NiIsImtpZCI6IjY3QjY2R1JSTEoiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJLNjlRNEc0M1E0IiwiaWF0IjoxNzYxMzA1MTc5LCJleHAiOjE3NzY4NTcxNzl9.hB2ORhgf2oC4HnMNjqEpPEFAeKSNqsajLAuinQUmWvxnkGrrsQbq0973AHe-HP5yNcb-YbLyEhN77jYYPGPfKA"
USER_TOKEN = "AqwChvUNtavngGqhAtUg4er4JgDox6+Ll+KQW/qdUEDFSdW3EGBAbcOvhhxcQddzwhjg3w9XAtMp8QQhFQ9cIaUQBeNyi817vdij7U5GMcTjK5vRunrLicz34BLD/cLuw/LEiFVZBOJRmo8FU/JtEfBSTdwGlx7VMAnzX1Dt7YVbyQo2yZH5rTDgF9v5XG8dAcDPBm/Y2V+cLE9bzVXxMC01141ALgwVcqbV/5cBfyWcH82+LQ=="

async def test_track(track_id, track_name):
    """Test a specific track ID to see what streams Apple provides."""

    print(f"\n{'='*60}")
    print(f"Testing: {track_name}")
    print(f"Track ID: {track_id}")
    print('='*60)

    async with aiohttp.ClientSession() as session:
        # 1. Get catalog track info
        catalog_url = f"https://api.music.apple.com/v1/catalog/us/songs/{track_id}"
        headers = {
            "Authorization": f"Bearer {APP_TOKEN}",
            "Music-User-Token": USER_TOKEN
        }

        try:
            async with session.get(catalog_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    track_data = data.get("data", [{}])[0]
                    attributes = track_data.get("attributes", {})

                    print(f"\n📝 Track Metadata:")
                    print(f"  Name: {attributes.get('name')}")
                    print(f"  Artist: {attributes.get('artistName')}")
                    print(f"  Audio Traits: {attributes.get('audioTraits', [])}")

                    if "atmos" in attributes.get("audioTraits", []):
                        print("  ✅ This track has DOLBY ATMOS in metadata!")
                    if "spatial" in attributes.get("audioTraits", []):
                        print("  ✅ This track has SPATIAL AUDIO in metadata!")
                    if "lossless" in attributes.get("audioTraits", []):
                        print("  ✅ This track has LOSSLESS in metadata!")
                else:
                    print(f"  ❌ Failed to get track info: {response.status}")

        except Exception as e:
            print(f"Error getting track info: {e}")

        # 2. Get playback info (requires webPlayback endpoint)
        playback_url = "https://play.music.apple.com/WebObjects/MZPlay.woa/wa/webPlayback"

        playback_data = {
            "salableAdamId": track_id
        }

        playback_headers = {
            "authorization": f"Bearer {APP_TOKEN}",
            "media-user-token": USER_TOKEN,
            "content-type": "application/json;charset=utf-8",
            "origin": "https://music.apple.com",
            "referer": "https://music.apple.com/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        try:
            async with session.post(playback_url, json=playback_data, headers=playback_headers) as response:
                if response.status == 200:
                    content = await response.json()

                    if "songList" in content and content["songList"]:
                        song = content["songList"][0]

                        print(f"\n🎵 Available Stream Formats:")

                        if "assets" in song:
                            assets = song["assets"]

                            # Check each asset
                            for asset in assets:
                                flavor = asset.get("flavor", "unknown")
                                url = asset.get("URL", "")

                                print(f"  - Flavor: {flavor}")

                                # Decode flavor
                                if "51:" in flavor:
                                    print("    → 🎵 SPATIAL/SURROUND FORMAT AVAILABLE!")
                                elif "28:" in flavor:
                                    print("    → Stereo format")

                                if "atmos" in flavor.lower():
                                    print("    → 🎉 DOLBY ATMOS STREAM!")
                                elif "ec3" in flavor:
                                    print("    → Dolby Digital Plus 5.1")
                                elif "ctrp256" in flavor:
                                    print("    → AAC 256kbps")
                                elif "ctrp64" in flavor:
                                    print("    → AAC 64kbps")
                        else:
                            print("  No assets found in response")

                        # Check for other audio indicators
                        if "audio-traits" in song:
                            print(f"\n  Song audio-traits: {song['audio-traits']}")

                        if "hls-key-server-url" in song:
                            print(f"  ✓ DRM key server available")

                    else:
                        print("No song data in response")

                else:
                    print(f"❌ Failed to get playback info: {response.status}")
                    error_text = await response.text()
                    print(f"Error: {error_text[:500]}")

        except Exception as e:
            print(f"Error getting playback info: {e}")

async def main():
    print("\n🔍 TESTING APPLE MUSIC API FOR SPATIAL AUDIO STREAMS")
    print("="*60)

    # Test known Dolby Atmos tracks
    test_tracks = [
        ("1440834467", "Billie Eilish - Bad Guy (known Atmos track)"),
        ("1544494722", "The Weeknd - Blinding Lights (known Atmos)"),
        ("1581087024", "Taylor Swift - Anti-Hero (known Atmos)"),
        ("1440841363", "Ariana Grande - 7 rings (known Atmos)"),
    ]

    for track_id, track_name in test_tracks:
        await test_track(track_id, track_name)
        await asyncio.sleep(1)  # Rate limiting

    print("\n" + "="*60)
    print("CONCLUSION:")
    print("="*60)
    print("""
If the tracks above show:
- audioTraits with 'atmos' but only 28: flavors → Apple restricts spatial to their apps
- No 51: flavors in assets → Spatial audio not available via Web API
- 51: flavors present → The patch should work

This will tell us if spatial audio is actually available through the API.
""")

if __name__ == "__main__":
    asyncio.run(main())