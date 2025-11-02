#!/usr/bin/env python3
"""
Start standalone Alexa OAuth server for Music Assistant integration.

Runs on port 8096 and registers OAuth endpoints:
- GET  /alexa/authorize
- POST /alexa/token
- GET  /health

This is a bridge between Tailscale Funnel (proxying to :8096) and the OAuth implementation.
"""

import sys
import os

# Add /data to path so we can import the OAuth module
sys.path.insert(0, '/data')

from aiohttp import web
import asyncio
from alexa_oauth_endpoints import (
    authorize_endpoint,
    token_endpoint
)

async def health_check(request):
    """Health check endpoint."""
    return web.json_response({
        'status': 'ok',
        'message': 'Music Assistant OAuth Server',
        'endpoints': [
            '/alexa/authorize',
            '/alexa/token',
            '/health'
        ]
    })

async def start_server():
    """Start the OAuth server."""
    app = web.Application()

    # Register routes
    app.router.add_get('/health', health_check)
    app.router.add_get('/alexa/authorize', authorize_endpoint)
    app.router.add_post('/alexa/token', token_endpoint)

    print("✅ Alexa OAuth Server Routes Registered:")
    print("   - GET  /health")
    print("   - GET  /alexa/authorize")
    print("   - POST /alexa/token")

    # Start server on port 8096
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8096)

    print("\n🚀 Starting Alexa OAuth Server on http://0.0.0.0:8096")
    await site.start()
    print("✅ Server running. Press Ctrl+C to stop.\n")

    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down...")
        await runner.cleanup()

if __name__ == '__main__':
    # Set environment variable for client secret
    if not os.getenv('ALEXA_OAUTH_CLIENT_SECRET'):
        os.environ['ALEXA_OAUTH_CLIENT_SECRET'] = 'Nv8Xh-zG_wR3mK2pL4jF9qY6bT5vC1xD0sW7aM'

    asyncio.run(start_server())
