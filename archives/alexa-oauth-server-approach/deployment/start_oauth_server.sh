#!/bin/sh
cd /data
python3 -c "
import sys
sys.path.insert(0, '/data')
sys.path.insert(0, '/app/venv/lib/python3.13/site-packages')

from aiohttp import web
from alexa_oauth_endpoints import authorize_endpoint, token_endpoint
import asyncio

async def health_check(request):
    return web.json_response({
        'status': 'ok',
        'message': 'Music Assistant OAuth Server',
        'endpoints': ['/alexa/authorize', '/alexa/token', '/health']
    })

async def start_server():
    app = web.Application()
    app.router.add_get('/alexa/authorize', authorize_endpoint)
    app.router.add_post('/alexa/token', token_endpoint)
    app.router.add_get('/health', health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8096)

    print('🚀 OAuth server starting on http://0.0.0.0:8096')
    await site.start()

    # Keep running
    while True:
        await asyncio.sleep(3600)

asyncio.run(start_server())
"
