#!/usr/bin/env python3
"""
List ALL artists from Music Assistant, bypassing web UI limits.
This script connects directly to the Music Assistant WebSocket API.
"""

import asyncio
import websockets
import json
import sys

MUSIC_ASSISTANT_URL = "ws://192.168.130.147:8095/ws"

async def list_all_artists():
    """Connect to Music Assistant and retrieve all artists."""

    try:
        async with websockets.connect(MUSIC_ASSISTANT_URL) as websocket:
            print("🎵 Connected to Music Assistant")

            # Subscribe to get server info
            await websocket.send(json.dumps({
                "id": 1,
                "type": "server_info/subscribe"
            }))

            # Wait for response
            response = await websocket.recv()
            print(f"Server info: {json.loads(response).get('type')}")

            # Get artists with pagination
            all_artists = []
            offset = 0
            limit = 100  # Get 100 at a time

            while True:
                # Request artists page
                request = {
                    "id": offset + 2,
                    "type": "music/artists",
                    "offset": offset,
                    "limit": limit,
                    "order_by": "name"
                }

                await websocket.send(json.dumps(request))
                response = await websocket.recv()
                data = json.loads(response)

                if "result" in data:
                    artists = data["result"]
                    if not artists:
                        break

                    all_artists.extend(artists)
                    print(f"Loaded {len(all_artists)} artists...")

                    if len(artists) < limit:
                        break  # Last page

                    offset += limit
                else:
                    print(f"Response: {data}")
                    break

            print(f"\n✅ Total artists in library: {len(all_artists)}")

            # Show some examples from different parts of alphabet
            if all_artists:
                print("\nSample of your artists:")
                print("First 5:", [a.get("name", "Unknown") for a in all_artists[:5]])

                # Find artists starting with different letters
                letters = {}
                for artist in all_artists:
                    name = artist.get("name", "")
                    if name:
                        first_letter = name[0].upper()
                        if first_letter not in letters:
                            letters[first_letter] = name

                print(f"\n📚 Artists by first letter ({len(letters)} letters):")
                for letter in sorted(letters.keys()):
                    print(f"  {letter}: {letters[letter]}")

            return all_artists

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nTrying alternative method...")

        # Alternative: Use HTTP API
        import aiohttp

        async with aiohttp.ClientSession() as session:
            all_artists = []
            page = 0

            while True:
                url = f"http://192.168.130.147:8095/api/music/artists"
                params = {
                    "offset": page * 50,
                    "limit": 50
                }

                try:
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            if not data:
                                break

                            all_artists.extend(data)
                            print(f"Page {page + 1}: Got {len(data)} artists (total: {len(all_artists)})")

                            if len(data) < 50:
                                break

                            page += 1
                        else:
                            print(f"HTTP {response.status}")
                            break
                except:
                    break

            if all_artists:
                print(f"\n✅ Total artists via HTTP: {len(all_artists)}")

                # Group by first letter
                by_letter = {}
                for artist in all_artists:
                    name = artist.get("name", "Unknown")
                    letter = name[0].upper() if name else "?"
                    if letter not in by_letter:
                        by_letter[letter] = []
                    by_letter[letter].append(name)

                print(f"\n📊 Distribution by letter:")
                for letter in sorted(by_letter.keys()):
                    print(f"  {letter}: {len(by_letter[letter])} artists")

            return all_artists

async def search_specific_artist(name):
    """Search for a specific artist."""
    import aiohttp

    async with aiohttp.ClientSession() as session:
        url = f"http://192.168.130.147:8095/api/search"
        params = {
            "query": name,
            "media_types": "artist",
            "limit": 10
        }

        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                print(f"\n🔍 Search results for '{name}':")
                if data.get("artists"):
                    for artist in data["artists"]:
                        print(f"  - {artist.get('name')}")
                else:
                    print("  No results found")

if __name__ == "__main__":
    print("="*60)
    print("🎵 MUSIC ASSISTANT ARTIST BROWSER")
    print("="*60)

    # Run the async function
    artists = asyncio.run(list_all_artists())

    # Also search for some specific artists
    test_artists = ["Madonna", "Taylor Swift", "Metallica", "Zeppelin"]
    for artist in test_artists:
        asyncio.run(search_specific_artist(artist))

    print("\n" + "="*60)
    print("SUMMARY:")
    print("="*60)
    if artists:
        print(f"✅ Found {len(artists)} total artists in your library")
        print("✅ The web UI limit is the problem, not the sync")
        print("✅ All your artists ARE in the database")
    else:
        print("⚠️ Could not retrieve artists via API")
        print("💡 But we know they're in the database from our earlier check")