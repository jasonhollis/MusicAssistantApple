#!/bin/bash
#
# Run Apple Music Playlist Debug Script
# This script extracts tokens from Music Assistant Docker and runs the debugger
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER_NAME="music-assistant"

echo "====================================================================="
echo "Apple Music Playlist Debugger - Token Extraction & Testing"
echo "====================================================================="

# Check if Docker container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "ERROR: Music Assistant container '${CONTAINER_NAME}' is not running"
    echo "Please start the container first"
    exit 1
fi

echo ""
echo "Step 1: Extracting tokens from Music Assistant..."
echo "---------------------------------------------------------------------"

# Extract the entire Apple Music provider config
APPLE_CONFIG=$(docker exec "${CONTAINER_NAME}" cat /data/settings.json 2>/dev/null | \
    python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    providers = data.get('providers', {})
    for key, value in providers.items():
        if 'apple_music' in key.lower():
            print(json.dumps(value, indent=2))
            break
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
")

if [ -z "$APPLE_CONFIG" ]; then
    echo "ERROR: Could not find Apple Music configuration"
    echo "Make sure Apple Music provider is configured in Music Assistant"
    exit 1
fi

echo "Apple Music config found:"
echo "$APPLE_CONFIG" | head -10

# Extract tokens
export MUSIC_APP_TOKEN=$(echo "$APPLE_CONFIG" | python3 -c "
import json, sys
config = json.load(sys.stdin)
print(config.get('music_app_token', ''))
")

export MUSIC_USER_TOKEN=$(echo "$APPLE_CONFIG" | python3 -c "
import json, sys
config = json.load(sys.stdin)
print(config.get('music_user_token', ''))
")

if [ -z "$MUSIC_APP_TOKEN" ]; then
    echo "ERROR: MUSIC_APP_TOKEN not found in config"
    exit 1
fi

if [ -z "$MUSIC_USER_TOKEN" ]; then
    echo "ERROR: MUSIC_USER_TOKEN not found in config"
    exit 1
fi

echo ""
echo "✓ Tokens extracted successfully"
echo "  App Token: ${MUSIC_APP_TOKEN:0:30}..."
echo "  User Token: ${MUSIC_USER_TOKEN:0:30}..."

echo ""
echo "Step 2: Running playlist debugger..."
echo "---------------------------------------------------------------------"

cd "$SCRIPT_DIR"

# Make sure we have required dependencies
if ! python3 -c "import aiohttp" 2>/dev/null; then
    echo "Installing aiohttp..."
    pip3 install aiohttp
fi

# Run the debug script
python3 debug_apple_playlists.py

echo ""
echo "====================================================================="
echo "Debug complete! Check output above for issues."
echo "====================================================================="
