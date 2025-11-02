#!/bin/bash
#
# Deploy Robust OAuth Server to Music Assistant Container
#

set -e

CONTAINER="addon_d5369777_music_assistant"
REMOTE_HOST="haboxhill.local"

echo "============================================"
echo "Deploying Robust OAuth Server"
echo "============================================"
echo ""

# Step 1: Copy files to container
echo "1. Copying files to container..."
scp -q robust_oauth_startup.py jason@${REMOTE_HOST}:/tmp/ || {
    echo "   ❌ Failed to copy file via SCP"
    echo "   Try manually: scp robust_oauth_startup.py jason@haboxhill.local:/tmp/"
    exit 1
}

echo "   ✅ Files copied to /tmp on ${REMOTE_HOST}"
echo ""

# Step 2: Deploy to container
echo "2. Deploying to Music Assistant container..."
ssh jason@${REMOTE_HOST} << 'ENDSSH'
    docker cp /tmp/robust_oauth_startup.py addon_d5369777_music_assistant:/data/
    docker exec addon_d5369777_music_assistant chmod +x /data/robust_oauth_startup.py
    echo "   ✅ Deployed to container at /data/robust_oauth_startup.py"
ENDSSH
echo ""

# Step 3: Check dependencies
echo "3. Checking dependencies in container..."
ssh jason@${REMOTE_HOST} << 'ENDSSH'
    MISSING=""

    if ! docker exec addon_d5369777_music_assistant python3 -c "import aiohttp" 2>/dev/null; then
        MISSING="${MISSING} aiohttp"
    fi

    if ! docker exec addon_d5369777_music_assistant python3 -c "from cryptography.fernet import Fernet" 2>/dev/null; then
        MISSING="${MISSING} cryptography"
    fi

    if [ -n "$MISSING" ]; then
        echo "   ⚠️  Missing dependencies:${MISSING}"
        echo "   Installing..."
        docker exec addon_d5369777_music_assistant sh -c "
            source /app/venv/bin/activate 2>/dev/null || true
            pip install${MISSING}
        " || {
            echo "   ❌ Failed to install dependencies"
            echo "   Run manually:"
            echo "   docker exec addon_d5369777_music_assistant sh -c \\"
            echo "     source /app/venv/bin/activate && pip install${MISSING}\""
            exit 1
        }
        echo "   ✅ Dependencies installed"
    else
        echo "   ✅ All dependencies present"
    fi
ENDSSH
echo ""

# Step 4: Start server
echo "4. Starting OAuth server..."
echo "   (Run in foreground - press Ctrl+C to stop)"
echo ""

ssh -t jason@${REMOTE_HOST} "docker exec -it addon_d5369777_music_assistant python3 /data/robust_oauth_startup.py"
