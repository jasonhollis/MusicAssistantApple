#!/usr/bin/env python3
"""
Register OAuth routes with Music Assistant web server

This script registers the OAuth authorization and token endpoints
with Music Assistant's aiohttp web server.

Run this inside the Music Assistant container to enable OAuth endpoints.
"""

import sys
sys.path.insert(0, '/data')
sys.path.insert(0, '/app/venv/lib/python3.13/site-packages')

print("🔧 Registering Alexa OAuth endpoints with Music Assistant...")

# Import OAuth endpoints module
try:
    from alexa_oauth_endpoints import register_oauth_routes, authorize_endpoint, token_endpoint
    print("✅ OAuth endpoints module imported successfully")
except ImportError as e:
    print(f"❌ Failed to import OAuth endpoints module: {e}")
    sys.exit(1)

# For standalone testing, we'll create a minimal aiohttp server
# In production, this would be integrated into Music Assistant's startup

from aiohttp import web
import asyncio

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

async def start_oauth_server():
    """Start standalone OAuth server for testing."""
    app = web.Application()

    # Register OAuth endpoints
    app.router.add_get('/alexa/authorize', authorize_endpoint)
    app.router.add_post('/alexa/token', token_endpoint)
    app.router.add_get('/health', health_check)

    print("\n✅ OAuth endpoints registered:")
    print("   - GET  /alexa/authorize (Authorization endpoint)")
    print("   - POST /alexa/token (Token endpoint)")
    print("   - GET  /health (Health check)")

    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8096)

    print("\n🚀 OAuth server starting on http://0.0.0.0:8096")
    print("   Listening for Alexa OAuth requests...")
    print("   Use Ctrl+C to stop")

    await site.start()

    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down OAuth server...")
        await runner.cleanup()

def test_integration():
    """Test that OAuth module can be integrated."""
    print("\n🧪 Testing OAuth integration...")

    # Verify endpoints are callable
    print("   ✅ authorize_endpoint:", callable(authorize_endpoint))
    print("   ✅ token_endpoint:", callable(token_endpoint))
    print("   ✅ register_oauth_routes:", callable(register_oauth_routes))

    # Show example integration code
    print("\n📋 Integration code for Music Assistant:")
    print("""
    # In Music Assistant startup (e.g., music_assistant/server/__init__.py):

    import sys
    sys.path.insert(0, '/data')
    from alexa_oauth_endpoints import register_oauth_routes

    # After web server is created:
    register_oauth_routes(mass.webserver.app)
    """)

    print("\n✅ OAuth integration test complete!")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Register Alexa OAuth endpoints')
    parser.add_argument('--standalone', action='store_true',
                       help='Run standalone OAuth server (for testing)')
    parser.add_argument('--test', action='store_true',
                       help='Test integration only (no server)')

    args = parser.parse_args()

    if args.standalone:
        # Run standalone server
        asyncio.run(start_oauth_server())
    elif args.test:
        # Just test integration
        test_integration()
    else:
        # Default: show usage
        print("""
Usage:
  python3 register_oauth_routes.py --test        # Test integration
  python3 register_oauth_routes.py --standalone  # Run standalone server

For production integration with Music Assistant:
  1. Edit Music Assistant startup code to call register_oauth_routes()
  2. OR run as standalone server on different port
  3. OR use Cloudflare Tunnel to proxy to standalone server
        """)
        test_integration()
