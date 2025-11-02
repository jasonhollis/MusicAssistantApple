#!/usr/bin/env python3
"""
Robust OAuth Server Startup Script

This script handles all common failure modes:
- Missing dependencies (auto-detects and reports)
- Dynamic Python version detection
- Comprehensive error logging
- Graceful failure with actionable error messages
"""

import sys
import os
import traceback
from pathlib import Path

# Setup logging BEFORE any imports that might fail
LOG_FILE = '/data/oauth_startup.log'

def log(message, also_print=True):
    """Write to log file AND optionally print."""
    with open(LOG_FILE, 'a') as f:
        f.write(f"{message}\n")
        f.flush()
    if also_print:
        print(message, flush=True)

# Clear previous log
with open(LOG_FILE, 'w') as f:
    f.write("=== OAuth Server Startup Log ===\n")

log("Step 1: Configuring Python paths...")

# Add /data to path
sys.path.insert(0, '/data')
log(f"  Added /data to sys.path")

# Dynamically find venv site-packages
import glob
venv_paths = glob.glob('/app/venv/lib/python3.*/site-packages')
if venv_paths:
    for path in venv_paths:
        sys.path.insert(0, path)
        log(f"  Added {path} to sys.path")
else:
    log("  ⚠️  WARNING: No venv site-packages found, using system Python")

log(f"  Python version: {sys.version}")
log(f"  Python executable: {sys.executable}")

# Step 2: Check dependencies
log("\nStep 2: Checking dependencies...")

missing_deps = []

try:
    import aiohttp
    log(f"  ✅ aiohttp {aiohttp.__version__}")
except ImportError as e:
    log(f"  ❌ aiohttp not available: {e}")
    missing_deps.append('aiohttp')

try:
    from cryptography.fernet import Fernet
    log(f"  ✅ cryptography available")
except ImportError as e:
    log(f"  ❌ cryptography not available: {e}")
    missing_deps.append('cryptography')

if missing_deps:
    error_msg = f"""
❌ MISSING DEPENDENCIES: {', '.join(missing_deps)}

Install with:
  docker exec addon_d5369777_music_assistant sh -c "
    source /app/venv/bin/activate
    pip install {' '.join(missing_deps)}
  "

Then restart the OAuth server.
"""
    log(error_msg)
    sys.exit(1)

# Step 3: Import OAuth module
log("\nStep 3: Importing OAuth endpoints module...")

try:
    from alexa_oauth_endpoints import authorize_endpoint, token_endpoint
    log("  ✅ OAuth endpoints imported successfully")
except Exception as e:
    log(f"  ❌ Failed to import OAuth endpoints: {e}")
    log(traceback.format_exc())
    sys.exit(1)

# Step 4: Import aiohttp web
log("\nStep 4: Importing aiohttp web framework...")

try:
    from aiohttp import web
    import asyncio
    log("  ✅ aiohttp.web imported")
except Exception as e:
    log(f"  ❌ Failed to import aiohttp.web: {e}")
    log(traceback.format_exc())
    sys.exit(1)

# Step 5: Create and start server
log("\nStep 5: Creating OAuth server...")

async def health_check(request):
    """Health check endpoint."""
    return web.json_response({
        'status': 'ok',
        'message': 'Music Assistant OAuth Server',
        'endpoints': ['/alexa/authorize', '/alexa/token', '/health']
    })

async def start_oauth_server():
    """Start standalone OAuth server."""
    try:
        log("  Creating web application...")
        app = web.Application()

        # Register routes
        app.router.add_get('/alexa/authorize', authorize_endpoint)
        app.router.add_post('/alexa/token', token_endpoint)
        app.router.add_get('/health', health_check)
        log("  ✅ Routes registered")

        # Setup runner
        log("  Setting up runner...")
        runner = web.AppRunner(app)
        await runner.setup()
        log("  ✅ Runner setup complete")

        # Create TCP site
        log("  Creating TCP site on 0.0.0.0:8096...")
        site = web.TCPSite(runner, '0.0.0.0', 8096)

        # Start listening
        log("  Starting server...")
        await site.start()

        log("\n" + "="*60)
        log("🚀 OAuth server running successfully!")
        log("="*60)
        log("   URL: http://0.0.0.0:8096")
        log("   Endpoints:")
        log("     - GET  /alexa/authorize")
        log("     - POST /alexa/token")
        log("     - GET  /health")
        log("="*60)

        # Keep running
        while True:
            await asyncio.sleep(3600)

    except OSError as e:
        if 'Address already in use' in str(e):
            log(f"  ❌ Port 8096 already in use!")
            log(f"     Run: docker exec addon_d5369777_music_assistant netstat -tuln | grep 8096")
        else:
            log(f"  ❌ Network error: {e}")
            log(traceback.format_exc())
        raise

    except Exception as e:
        log(f"  ❌ Server startup failed: {e}")
        log(traceback.format_exc())
        raise

# Step 6: Run server
log("\nStep 6: Starting asyncio event loop...")

try:
    asyncio.run(start_oauth_server())
except KeyboardInterrupt:
    log("\n⏹️  Server stopped by user (Ctrl+C)")
except Exception as e:
    log(f"\n❌ FATAL ERROR: {e}")
    log(traceback.format_exc())
    sys.exit(1)
