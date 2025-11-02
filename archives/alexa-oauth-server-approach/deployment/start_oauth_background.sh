#!/bin/bash
#
# Start OAuth Server in Background (Detached Mode)
# Run this AFTER deploy_robust_oauth.sh has confirmed server works in foreground
#

CONTAINER="addon_d5369777_music_assistant"
REMOTE_HOST="haboxhill.local"

echo "============================================"
echo "Starting OAuth Server in Background"
echo "============================================"
echo ""

# Check if already running
echo "1. Checking for existing OAuth server process..."
ssh jason@${REMOTE_HOST} << 'ENDSSH'
    EXISTING=$(docker exec addon_d5369777_music_assistant ps aux | grep -v grep | grep robust_oauth_startup || true)
    if [ -n "$EXISTING" ]; then
        echo "   ⚠️  OAuth server already running:"
        echo "$EXISTING"
        echo ""
        echo "   To stop: docker exec addon_d5369777_music_assistant pkill -f robust_oauth_startup"
        exit 1
    else
        echo "   ✅ No existing OAuth server found"
    fi
ENDSSH
echo ""

# Start in background using nohup
echo "2. Starting OAuth server in background..."
ssh jason@${REMOTE_HOST} << 'ENDSSH'
    docker exec -d addon_d5369777_music_assistant sh -c "
        nohup python3 /data/robust_oauth_startup.py > /data/oauth_output.log 2>&1 &
        echo \$! > /data/oauth_server.pid
    "
    sleep 2
ENDSSH
echo "   ✅ Server started"
echo ""

# Verify it's running
echo "3. Verifying server is running..."
ssh jason@${REMOTE_HOST} << 'ENDSSH'
    sleep 1

    # Check process
    if docker exec addon_d5369777_music_assistant ps aux | grep -v grep | grep -q robust_oauth_startup; then
        echo "   ✅ Process is running"

        # Get PID
        PID=$(docker exec addon_d5369777_music_assistant cat /data/oauth_server.pid 2>/dev/null || echo "unknown")
        echo "   PID: $PID"

        # Check logs
        echo ""
        echo "   Last 10 lines of startup log:"
        docker exec addon_d5369777_music_assistant tail -10 /data/oauth_startup.log || echo "   (log not yet created)"

        echo ""
        echo "   Testing health endpoint..."
        if docker exec addon_d5369777_music_assistant wget -q -O- http://localhost:8096/health 2>/dev/null; then
            echo ""
            echo "   ✅ Health check passed!"
        else
            echo "   ⚠️  Health check failed (server may still be starting...)"
        fi
    else
        echo "   ❌ Process not running!"
        echo ""
        echo "   Check startup log:"
        docker exec addon_d5369777_music_assistant cat /data/oauth_startup.log
        exit 1
    fi
ENDSSH
echo ""

echo "============================================"
echo "OAuth Server Status"
echo "============================================"
echo ""
echo "Logs:"
echo "  Startup: docker exec $CONTAINER cat /data/oauth_startup.log"
echo "  Output:  docker exec $CONTAINER tail -f /data/oauth_output.log"
echo ""
echo "Control:"
echo "  Stop:    docker exec $CONTAINER pkill -f robust_oauth_startup"
echo "  Restart: $0"
echo ""
echo "Health Check:"
echo "  curl http://haboxhill.local:8096/health"
echo ""
