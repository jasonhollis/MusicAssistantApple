#!/bin/bash
#
# Quick verification that the bug exists in the current code
#

PROVIDER_FILE="server-2.6.0/music_assistant/providers/apple_music/__init__.py"

echo "====================================================================="
echo "Verifying Apple Music Playlist Bug Exists"
echo "====================================================================="
echo ""

if [ ! -f "$PROVIDER_FILE" ]; then
    echo "✗ Provider file not found: $PROVIDER_FILE"
    exit 1
fi

echo "Checking for buggy code pattern..."
echo ""

# Look for the buggy line
if grep -n 'if response.status == 404 and "limit" in kwargs and "offset" in kwargs:' "$PROVIDER_FILE" | head -1; then
    echo ""
    echo "✓ Found the 404 pagination handler"

    # Check if it's the buggy version or fixed version
    LINE_NUM=$(grep -n 'if response.status == 404 and "limit" in kwargs and "offset" in kwargs:' "$PROVIDER_FILE" | head -1 | cut -d: -f1)

    # Get next few lines to see if it's fixed
    CONTEXT=$(sed -n "${LINE_NUM},$((LINE_NUM + 5))p" "$PROVIDER_FILE")

    echo ""
    echo "Code context:"
    echo "$CONTEXT"
    echo ""

    if echo "$CONTEXT" | grep -q 'if kwargs.get("offset", 0) > 0:'; then
        echo "✓ CODE APPEARS TO BE FIXED"
        echo "  The offset check is present"
        echo "  Playlists should sync correctly"
    elif echo "$CONTEXT" | grep -q 'return {}' | head -1; then
        echo "✗ BUG CONFIRMED"
        echo "  The code returns {} without checking offset"
        echo "  This will break playlist sync on first page"
        echo ""
        echo "Run the fix script to patch this:"
        echo "  python3 apple_music_playlist_sync_fix.py"
    else
        echo "? UNCLEAR"
        echo "  Cannot determine if bug is present"
        echo "  Manual inspection needed"
    fi
else
    echo "✗ Could not find the 404 handler"
    echo "  The code may have been modified already"
fi

echo ""
echo "====================================================================="
echo "Bug verification complete"
echo "====================================================================="
