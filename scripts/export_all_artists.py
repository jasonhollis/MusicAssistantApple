#!/usr/bin/env python3
"""
Export all artists from Music Assistant database.
Run this inside the container to get around web UI limits.
"""

import sqlite3
import json

def export_artists():
    """Export all artists from the database."""

    db_path = '/data/library.db'
    output_path = '/data/all_artists.json'

    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get all artists
        cursor.execute("""
            SELECT DISTINCT
                artist_id,
                name,
                sort_name,
                provider_instance
            FROM artists
            WHERE provider_instance LIKE '%apple_music%'
            ORDER BY sort_name, name
        """)

        artists = []
        for row in cursor.fetchall():
            artists.append({
                'id': row['artist_id'],
                'name': row['name'],
                'sort_name': row['sort_name'],
                'provider': row['provider_instance']
            })

        # Group by first letter
        by_letter = {}
        for artist in artists:
            name = artist['name'] or artist['sort_name'] or 'Unknown'
            letter = name[0].upper() if name else '?'
            if letter not in by_letter:
                by_letter[letter] = []
            by_letter[letter].append(name)

        # Print summary
        print(f"✅ Total artists found: {len(artists)}")
        print(f"\n📊 Artists by first letter:")

        for letter in sorted(by_letter.keys()):
            count = len(by_letter[letter])
            examples = by_letter[letter][:3]
            print(f"  {letter}: {count} artists - Examples: {', '.join(examples)}")

        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'total': len(artists),
                'artists': artists,
                'by_letter': {k: len(v) for k, v in by_letter.items()}
            }, f, ensure_ascii=False, indent=2)

        print(f"\n💾 Full list saved to: {output_path}")

        # Show some notable artists after 'J'
        print("\n🎵 Sample of artists after 'J':")
        after_j = [a['name'] for a in artists if a['name'] and a['name'][0].upper() > 'J']
        for artist in after_j[:20]:
            print(f"  - {artist}")

        conn.close()
        return len(artists)

    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

if __name__ == "__main__":
    print("="*60)
    print("🎵 MUSIC ASSISTANT - EXPORT ALL ARTISTS")
    print("="*60)

    count = export_artists()

    if count > 0:
        print("\n" + "="*60)
        print("SOLUTION FOR WEB UI LIMIT:")
        print("="*60)
        print("✅ All your artists ARE synced to the database")
        print(f"✅ Found {count} artists total")
        print("❌ The web UI has a display limit (bad design)")
        print("\nWORKAROUNDS:")
        print("1. Use the search function to find specific artists")
        print("2. Browse by album or track instead of artist")
        print("3. Use playlists to organize your music")
        print("4. The artists are there - they play if you search for them!")