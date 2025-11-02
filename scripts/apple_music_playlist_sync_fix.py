#!/usr/bin/env python3
"""
Apple Music Playlist Sync Fix

This patch fixes the bug where playlists return 0 items during sync.

ROOT CAUSE:
The _get_data method returns {} when it gets a 404 with pagination params.
This breaks _get_all_items on the first page for endpoints that don't
support limit/offset, causing it to return an empty list immediately.

FIX:
Only return empty dict for 404 with pagination when offset > 0.
For offset=0 (first page), raise MediaNotFoundError as normal.

USAGE:
    python3 apple_music_playlist_sync_fix.py

This will create a patched version of the Apple Music provider.
"""

import sys
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent
PROVIDER_FILE = SCRIPT_DIR / "server-2.6.0/music_assistant/providers/apple_music/__init__.py"
BACKUP_FILE = PROVIDER_FILE.with_suffix(".py.backup")


def create_backup():
    """Create backup of original file."""
    if BACKUP_FILE.exists():
        print(f"Backup already exists: {BACKUP_FILE}")
        response = input("Overwrite backup? (y/n): ")
        if response.lower() != 'y':
            print("Using existing backup")
            return False

    import shutil
    shutil.copy2(PROVIDER_FILE, BACKUP_FILE)
    print(f"✓ Backup created: {BACKUP_FILE}")
    return True


def apply_fix():
    """Apply the playlist sync fix."""
    print("\n" + "="*80)
    print("APPLYING APPLE MUSIC PLAYLIST SYNC FIX")
    print("="*80)

    # Read the file
    print(f"\nReading: {PROVIDER_FILE}")
    with open(PROVIDER_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
        lines = content.split('\n')

    # Find the problematic code (around line 799-800)
    print("\nSearching for buggy 404 handler...")

    buggy_pattern = 'if response.status == 404 and "limit" in kwargs and "offset" in kwargs:'
    fixed_pattern_exists = 'if kwargs.get("offset", 0) > 0:'

    # Check if already patched
    if fixed_pattern_exists in content:
        print("✓ File already patched!")
        return True

    # Find and replace
    found = False
    for i, line in enumerate(lines):
        if buggy_pattern in line:
            found = True
            line_num = i + 1
            print(f"✓ Found buggy code at line {line_num}")

            # Get indentation
            indent = len(line) - len(line.lstrip())
            base_indent = ' ' * indent
            inner_indent = ' ' * (indent + 4)

            # Create the fix
            new_code = [
                f"{base_indent}if response.status == 404 and \"limit\" in kwargs and \"offset\" in kwargs:",
                f"{inner_indent}# Only return empty for pagination beyond first page",
                f"{inner_indent}# For offset=0, this might indicate endpoint doesn't support pagination",
                f"{inner_indent}if kwargs.get(\"offset\", 0) > 0:",
                f"{inner_indent}    # Beyond first page, treat 404 as end of results",
                f"{inner_indent}    return {{}}",
                f"{inner_indent}# For first page (offset=0), let it fall through to normal 404 handling"
            ]

            # Replace the line
            lines[i] = '\n'.join(new_code)

            # Find and remove the old "return {}" line
            if i + 1 < len(lines) and "return {}" in lines[i + 1]:
                lines[i + 1] = ""  # Remove old return line

            print("\nOriginal code:")
            print(f"  Line {line_num}: {line}")
            if i + 1 < len(lines):
                print(f"  Line {line_num + 1}: {lines[i + 1]}")

            print("\nNew code:")
            for idx, new_line in enumerate(new_code, start=line_num):
                print(f"  Line {idx}: {new_line}")

            break

    if not found:
        print("✗ Could not find the buggy code!")
        print("The file may have been modified already.")
        return False

    # Write the fixed content
    print(f"\nWriting fixed code to: {PROVIDER_FILE}")
    with open(PROVIDER_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print("✓ Fix applied successfully!")
    return True


def add_logging_enhancement():
    """Add enhanced logging to help diagnose issues."""
    print("\n" + "="*80)
    print("ADDING ENHANCED LOGGING")
    print("="*80)

    with open(PROVIDER_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if logging already added
    if "Pagination 404 detected" in content:
        print("✓ Logging already enhanced!")
        return True

    # Find the get_library_playlists method
    target = 'async def get_library_playlists(self) -> AsyncGenerator[Playlist, None]:'

    if target not in content:
        print("✗ Could not find get_library_playlists method")
        return False

    # Add logging after the endpoint definition
    old_code = '''    async def get_library_playlists(self) -> AsyncGenerator[Playlist, None]:
        """Retrieve playlists from the provider."""
        endpoint = "me/library/playlists"
        for item in await self._get_all_items(endpoint):'''

    new_code = '''    async def get_library_playlists(self) -> AsyncGenerator[Playlist, None]:
        """Retrieve playlists from the provider."""
        endpoint = "me/library/playlists"
        self.logger.debug("Fetching library playlists from endpoint: %s", endpoint)
        items = await self._get_all_items(endpoint)
        self.logger.info("Retrieved %d library playlist items from Apple Music API", len(items))
        for item in items:'''

    content = content.replace(old_code, new_code)

    with open(PROVIDER_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✓ Enhanced logging added!")
    return True


def verify_fix():
    """Verify the fix was applied correctly."""
    print("\n" + "="*80)
    print("VERIFYING FIX")
    print("="*80)

    with open(PROVIDER_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = [
        ('Offset check added', 'if kwargs.get("offset", 0) > 0:'),
        ('Nested return statement', 'return {}'),
        ('Comment about first page', 'For first page (offset=0)'),
    ]

    all_passed = True
    for check_name, pattern in checks:
        if pattern in content:
            print(f"✓ {check_name}")
        else:
            print(f"✗ {check_name} - FAILED")
            all_passed = False

    if all_passed:
        print("\n✓ All verification checks passed!")
    else:
        print("\n✗ Some verification checks failed!")

    return all_passed


def show_next_steps():
    """Show what to do next."""
    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print()
    print("1. Test the fix by running the debug script:")
    print("   ./run_playlist_debug.sh")
    print()
    print("2. Restart Music Assistant to load the patched provider:")
    print("   docker restart music-assistant")
    print()
    print("3. Trigger a playlist sync in Music Assistant UI")
    print()
    print("4. Check logs for the enhanced logging:")
    print("   docker logs music-assistant | grep -i playlist")
    print()
    print("5. Verify playlists appear in Music Assistant")
    print()
    print("If issues occur, restore from backup:")
    print(f"   cp {BACKUP_FILE} {PROVIDER_FILE}")
    print("   docker restart music-assistant")
    print()


def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("APPLE MUSIC PLAYLIST SYNC FIX")
    print("="*80)
    print()
    print("This will patch the Apple Music provider to fix playlist syncing.")
    print()

    if not PROVIDER_FILE.exists():
        print(f"✗ Provider file not found: {PROVIDER_FILE}")
        return 1

    print(f"Provider file: {PROVIDER_FILE}")
    print()

    response = input("Continue with patching? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled")
        return 0

    # Create backup
    create_backup()

    # Apply fix
    if not apply_fix():
        print("\n✗ Fix failed!")
        return 1

    # Add logging
    add_logging_enhancement()

    # Verify
    if not verify_fix():
        print("\n⚠️  Verification failed - fix may not work correctly")
        response = input("Restore from backup? (y/n): ")
        if response.lower() == 'y':
            import shutil
            shutil.copy2(BACKUP_FILE, PROVIDER_FILE)
            print("✓ Restored from backup")
        return 1

    # Success
    print("\n" + "="*80)
    print("✓ FIX APPLIED SUCCESSFULLY!")
    print("="*80)

    show_next_steps()

    return 0


if __name__ == "__main__":
    sys.exit(main())
