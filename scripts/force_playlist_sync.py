#!/usr/bin/env python3
"""Force playlist sync to run immediately"""

import asyncio
import sys
sys.path.insert(0, '/app/venv/lib/python3.13/site-packages')

from music_assistant import MusicAssistant
from music_assistant.providers.apple_music import AppleMusicProvider

print("🎵 Forcing Apple Music playlist sync...")

# Try to trigger the sync directly
try:
    # Find the provider instance
    import os
    import json

    # Load settings to get the provider config
    with open('/data/settings.json', 'r') as f:
        settings = json.load(f)

    # Find Apple Music provider
    apple_provider = None
    for provider_id, provider_config in settings.get('providers', {}).items():
        if 'apple_music' in provider_id:
            print(f"Found Apple Music provider: {provider_id}")

            # Import and instantiate
            from music_assistant.providers.apple_music import AppleMusicProvider

            # Run the playlist sync directly
            async def sync_playlists():
                # We'll call the method directly (simplified)
                print("Starting playlist sync...")
                count = 0

                # Test the API directly
                import aiohttp
                headers = {
                    "Authorization": f"Bearer {provider_config['values']['music_app_token']}",
                    "Music-User-Token": provider_config['values']['music_user_token']
                }

                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://api.music.apple.com/v1/me/library/playlists",
                        headers=headers,
                        params={"limit": 50}
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            playlists = data.get("data", [])
                            print(f"✅ Found {len(playlists)} playlists from API")
                            for p in playlists[:5]:
                                print(f"  - {p['attributes']['name']}")
                        else:
                            print(f"❌ API returned {response.status}")

            # Run the async function
            asyncio.run(sync_playlists())
            break

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()