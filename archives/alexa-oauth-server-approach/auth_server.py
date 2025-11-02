#!/usr/bin/env python3
"""
Standalone OAuth 2.0 Authorization Server for Music Assistant Alexa Integration

This runs the OAuth endpoints as a standalone web server on port 5001.
It will be integrated into Music Assistant's main web server later.

Usage:
    python3 auth_server.py

Endpoints:
    - GET  /alexa/authorize - Authorization endpoint (redirects to Alexa with code)
    - POST /alexa/token - Token endpoint (exchanges code for access token)
    - GET  /health - Health check endpoint
"""

import os
import sys
from aiohttp import web
import asyncio

# Import the OAuth endpoint handlers
import alexa_oauth_endpoints


async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint for monitoring."""
    return web.json_response({
        'status': 'ok',
        'service': 'alexa-oauth-server',
        'endpoints': {
            'authorize': '/alexa/authorize',
            'token': '/alexa/token'
        }
    })


def create_app() -> web.Application:
    """Create and configure the aiohttp application."""
    app = web.Application()

    # Register OAuth endpoints
    app.router.add_get('/alexa/authorize', alexa_oauth_endpoints.authorize_endpoint)
    app.router.add_post('/alexa/token', alexa_oauth_endpoints.token_endpoint)

    # Health check
    app.router.add_get('/health', health_check)

    return app


async def main():
    """Start the OAuth server."""
    app = create_app()

    # Get port from environment or use default
    port = int(os.getenv('OAUTH_PORT', 5001))
    host = os.getenv('OAUTH_HOST', '0.0.0.0')

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, host, port)
    await site.start()

    print("=" * 80)
    print(f"OAuth 2.0 Authorization Server started on http://{host}:{port}")
    print("=" * 80)
    print()
    print("Endpoints:")
    print(f"  - GET  http://{host}:{port}/alexa/authorize")
    print(f"  - POST http://{host}:{port}/alexa/token")
    print(f"  - GET  http://{host}:{port}/health")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 80)

    # Keep server running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\nShutting down...")
        await runner.cleanup()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped")
        sys.exit(0)
