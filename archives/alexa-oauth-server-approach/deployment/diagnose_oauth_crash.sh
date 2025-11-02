#!/bin/bash
#
# OAuth Server Crash Diagnostic Script
# Run this on haboxhill.local to identify the root cause
#

set -e

echo "============================================"
echo "OAuth Server Crash Diagnostic"
echo "============================================"
echo ""

CONTAINER="addon_d5369777_music_assistant"

# 1. Verify container is running
echo "1. Container Status Check:"
if docker ps | grep -q "$CONTAINER"; then
    echo "   ✅ Container is running"
else
    echo "   ❌ Container is NOT running"
    exit 1
fi
echo ""

# 2. Check Python syntax
echo "2. Python Syntax Check:"
if docker exec "$CONTAINER" python3 -m py_compile /data/alexa_oauth_endpoints.py 2>&1; then
    echo "   ✅ No syntax errors in alexa_oauth_endpoints.py"
else
    echo "   ❌ SYNTAX ERROR FOUND - This is the crash cause!"
    exit 1
fi
echo ""

# 3. Test imports
echo "3. Import Test:"
docker exec "$CONTAINER" python3 << 'ENDPYTHON'
import sys
sys.path.insert(0, '/data')
sys.path.insert(0, '/app/venv/lib/python3.13/site-packages')

try:
    from alexa_oauth_endpoints import authorize_endpoint, token_endpoint
    print('   ✅ Imports successful')
except Exception as e:
    print(f'   ❌ Import error: {e}')
    import traceback
    traceback.print_exc()
    sys.exit(1)
ENDPYTHON
echo ""

# 4. Check dependencies
echo "4. Dependency Check:"
echo "   - aiohttp:"
if docker exec "$CONTAINER" python3 -c "import aiohttp; print(f'     ✅ Version {aiohttp.__version__}')" 2>&1; then
    :
else
    echo "     ❌ aiohttp NOT AVAILABLE - Install with: pip install aiohttp"
    exit 1
fi

echo "   - cryptography:"
if docker exec "$CONTAINER" python3 -c "from cryptography.fernet import Fernet; print('     ✅ Available')" 2>&1; then
    :
else
    echo "     ❌ cryptography NOT AVAILABLE - Install with: pip install cryptography"
    exit 1
fi
echo ""

# 5. Test server initialization (without starting)
echo "5. Server Initialization Test:"
docker exec "$CONTAINER" python3 << 'ENDPYTHON'
import sys
import traceback
sys.path.insert(0, '/data')
sys.path.insert(0, '/app/venv/lib/python3.13/site-packages')

try:
    from alexa_oauth_endpoints import authorize_endpoint, token_endpoint
    from aiohttp import web
    import asyncio

    async def test_init():
        try:
            app = web.Application()
            app.router.add_get('/alexa/authorize', authorize_endpoint)
            app.router.add_post('/alexa/token', token_endpoint)
            runner = web.AppRunner(app)
            await runner.setup()
            print('   ✅ Server initialization successful')
            await runner.cleanup()
        except Exception as e:
            print(f'   ❌ Server initialization failed: {e}')
            traceback.print_exc()
            raise

    asyncio.run(test_init())

except Exception as e:
    print(f'   ❌ CRASH DETECTED: {e}')
    traceback.print_exc()
    sys.exit(1)
ENDPYTHON
echo ""

# 6. Test actual startup (5 second run)
echo "6. Live Server Test (5 seconds):"
docker exec "$CONTAINER" timeout 5 python3 << 'ENDPYTHON' || true
import sys
import traceback
sys.path.insert(0, '/data')
sys.path.insert(0, '/app/venv/lib/python3.13/site-packages')

try:
    from alexa_oauth_endpoints import authorize_endpoint, token_endpoint
    from aiohttp import web
    import asyncio

    async def test_server():
        app = web.Application()
        app.router.add_get('/alexa/authorize', authorize_endpoint)
        app.router.add_post('/alexa/token', token_endpoint)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8096)

        print('   🚀 Server starting on 0.0.0.0:8096...')
        await site.start()
        print('   ✅ Server running (waiting 5 seconds)...')

        # Run for 5 seconds
        await asyncio.sleep(5)

        print('   ✅ Server survived 5 seconds!')
        await runner.cleanup()

    asyncio.run(test_server())

except KeyboardInterrupt:
    print('   ✅ Server terminated gracefully (timeout)')
except Exception as e:
    print(f'   ❌ SERVER CRASH: {e}')
    traceback.print_exc()
    sys.exit(1)
ENDPYTHON
echo ""

# 7. Check file permissions
echo "7. File Permissions Check:"
docker exec "$CONTAINER" ls -la /data/*.py | grep -E "(alexa|oauth|register)"
echo ""

# 8. Check if config file exists
echo "8. Config File Check:"
if docker exec "$CONTAINER" test -f /data/oauth_clients.json; then
    echo "   ✅ oauth_clients.json exists"
    docker exec "$CONTAINER" python3 -c "
import json
with open('/data/oauth_clients.json') as f:
    config = json.load(f)
    print(f'   ✅ Valid JSON with {len(config)} clients configured')
"
else
    echo "   ⚠️  oauth_clients.json missing (will use defaults)"
fi
echo ""

echo "============================================"
echo "Diagnostic Complete"
echo "============================================"
echo ""
echo "If all checks pass, the issue may be:"
echo "1. Running in detached mode (-d) loses error output"
echo "2. File descriptor/logging redirection issue"
echo "3. Docker resource limits"
echo ""
echo "Next steps:"
echo "- Run server in foreground (remove -d flag) to see real-time output"
echo "- Check Docker logs: docker logs addon_d5369777_music_assistant"
echo "- Monitor process: docker exec addon_d5369777_music_assistant ps aux | grep python"
