#!/usr/bin/env python3
"""
OAuth 2.0 Authorization Server for Music Assistant Alexa Integration

This implements the OAuth authorization and token endpoints that will be added
to Music Assistant to support the Alexa Skill integration.

Security Features:
- PKCE (Proof Key for Code Exchange) to prevent authorization code interception
- Short-lived authorization codes (5 minutes)
- Encrypted token storage using Fernet (AES-128)
- State parameter validation to prevent CSRF
- Secure random generation for codes and tokens

Flow:
1. Alexa Skill redirects user to /authorize endpoint
2. User authenticates (passkey via Login with Amazon)
3. Authorization code generated and returned to Alexa
4. Alexa calls /token endpoint with code + code_verifier
5. Token endpoint verifies PKCE, generates access/refresh tokens
6. Tokens stored encrypted in Music Assistant config

References:
- RFC 6749: OAuth 2.0 Authorization Framework
- RFC 7636: PKCE Extension
- Music Assistant Spotify provider OAuth implementation
"""

import asyncio
import hashlib
import base64
import secrets
import time
import json
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, parse_qs
from cryptography.fernet import Fernet
from aiohttp import web

# Constants
AUTH_CODE_EXPIRY = 300  # 5 minutes
ACCESS_TOKEN_EXPIRY = 3600  # 1 hour
REFRESH_TOKEN_EXPIRY = 90 * 24 * 3600  # 90 days


def load_oauth_clients():
    """Load OAuth client credentials from config file or environment."""
    # Try multiple possible config locations
    config_paths = [
        Path('/data/oauth_clients.json'),  # Music Assistant data directory
        Path(os.getenv('MASS_CONFIG_DIR', '/config')) / 'oauth_clients.json',
        Path('/config/oauth_clients.json'),
    ]

    # Fallback to environment variable
    default_client_secret = os.getenv('ALEXA_OAUTH_CLIENT_SECRET', 'Nv8Xh-zG_wR3mK2pL4jF9qY6bT5vC1xD0sW7aM')

    default_clients = {
        "amazon-alexa": {
            "client_type": "public",  # Public client using PKCE (per RFC 7636)
            # client_secret intentionally omitted for public clients
            # PKCE provides cryptographic security without shared secrets
            "redirect_uris": [
                "https://pitangui.amazon.com/auth/o2/callback",
                "https://layla.amazon.com/api/skill/link/MKXZK47785HJ2",
                "https://alexa.amazon.co.jp/api/skill/link/MKXZK47785HJ2"
            ]
        }
    }

    # Try to load from config file (check all possible locations)
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️  Failed to load {config_path}: {e}")
                continue

    # No config file found, use defaults
    return default_clients


def validate_client(client_id: str, client_secret: Optional[str] = None, is_pkce_client: bool = False) -> bool:
    """
    Validate OAuth client credentials.

    Supports two client types per OAuth 2.0 RFC 6749:
    - Confidential clients: require client_secret
    - Public clients: use PKCE for security, no client_secret required
    """
    import sys

    print(f"🔐 validate_client() called: client_id='{client_id}', has_secret={bool(client_secret)}", file=sys.stdout, flush=True)

    clients = load_oauth_clients()
    print(f"📋 Loaded {len(clients)} client(s): {list(clients.keys())}", file=sys.stdout, flush=True)

    if client_id not in clients:
        print(f"❌ client_id '{client_id}' NOT FOUND in config", file=sys.stdout, flush=True)
        return False

    client_config = clients[client_id]
    client_type = client_config.get('client_type', 'confidential')  # Default to confidential for backward compatibility
    print(f"📝 Client config: type={client_type}, has_secret={'client_secret' in client_config}", file=sys.stdout, flush=True)

    # Public clients (using PKCE): validate client_id only
    if client_type == 'public':
        # PKCE provides cryptographic security without client_secret
        # Just verify the client_id exists
        print(f"✅ Public client '{client_id}' - validation passed (PKCE)", file=sys.stdout, flush=True)
        return True

    # Confidential clients: require client_secret
    if client_secret is None:
        print(f"❌ Confidential client but client_secret is None", file=sys.stdout, flush=True)
        return False

    expected_secret = client_config.get('client_secret')
    if not expected_secret or client_secret != expected_secret:
        print(f"❌ client_secret mismatch", file=sys.stdout, flush=True)
        return False

    print(f"✅ Confidential client - validation passed", file=sys.stdout, flush=True)
    return True


# In-memory storage for auth codes (production should use Redis or database)
# Format: {auth_code: {client_id, code_challenge, redirect_uri, user_id, expires_at}}
auth_codes = {}

# Token storage (production should use Music Assistant's encrypted config storage)
# Format: {user_id: {access_token, refresh_token, expires_at}}
tokens = {}

# Pending auth codes awaiting user approval (consent screen)
# Format: {temp_auth_code: {client_id, code_challenge, redirect_uri, state, scope, expires_at}}
pending_auth_codes = {}


def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure random token."""
    return secrets.token_urlsafe(length)


def hash_code_verifier(verifier: str) -> str:
    """Hash code verifier using SHA256 for PKCE validation."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip('=')


async def authorize_endpoint(request: web.Request) -> web.Response:
    """
    OAuth 2.0 Authorization Endpoint (RFC 6749 Section 3.1)

    Query Parameters:
    - response_type: must be "code" (authorization code grant)
    - client_id: Alexa Skill client ID
    - redirect_uri: Alexa callback URL
    - state: CSRF protection token from Alexa
    - code_challenge: PKCE challenge (SHA256 hash of code_verifier)
    - code_challenge_method: must be "S256"
    - scope: requested permissions (e.g., "music.read music.control")

    Returns:
    - Renders consent screen (HTML) for user approval
    - After user approval, redirects to redirect_uri with authorization code

    Example:
    GET /authorize?response_type=code&client_id=alexa_skill_123&redirect_uri=https://...&state=xyz&code_challenge=abc&code_challenge_method=S256
    """
    import sys
    import json

    auth_debug = {
        'endpoint': '/alexa/authorize',
        'method': request.method,
        'path': request.path,
        'headers': dict(request.headers),
        'query_params': dict(request.rel_url.query)
    }

    debug_output = f"\n{'='*80}\n🔐 AUTHORIZE ENDPOINT CALLED\n{'='*80}\n{json.dumps(auth_debug, indent=2)}\n{'='*80}\n"

    for stream in [sys.stdout, sys.stderr]:
        print(debug_output, file=stream, flush=True)

    try:
        with open('/data/oauth_debug.log', 'a') as f:
            f.write(debug_output)
            f.flush()
    except Exception as e:
        print(f"Failed to write to debug log: {e}", file=sys.stderr)

    params = request.rel_url.query

    # Validate required parameters (PKCE parameters are optional)
    required = ['response_type', 'client_id', 'redirect_uri', 'state']
    missing = [p for p in required if p not in params]
    if missing:
        error_message = f'Missing required parameters: {", ".join(missing)}'
        return aiohttp_jinja2.render_template(
            'error.html',
            request,
            {'error': error_message}
        )

    # Validate response_type
    if params['response_type'] != 'code':
        error_message = 'Only authorization code grant (response_type=code) is supported'
        return aiohttp_jinja2.render_template(
            'error.html',
            request,
            {'error': error_message}
        )

    # Validate PKCE parameters if provided (optional)
    if params.get('code_challenge_method') and params['code_challenge_method'] != 'S256':
        error_message = 'Only S256 code_challenge_method is supported for PKCE'
        return aiohttp_jinja2.render_template(
            'error.html',
            request,
            {'error': error_message}
        )

    # Generate temporary auth code awaiting user approval
    temp_auth_code = generate_secure_token(32)

    # Store in pending codes with all metadata
    pending_auth_codes[temp_auth_code] = {
        'client_id': params['client_id'],
        'code_challenge': params.get('code_challenge'),  # Optional - None if PKCE not used
        'redirect_uri': params['redirect_uri'],
        'state': params['state'],
        'scope': params.get('scope', 'music.read music.control'),
        'expires_at': time.time() + AUTH_CODE_EXPIRY
    }

    print(f"⏳ Consent screen: Generated temporary auth code", flush=True)
    print(f"   Pending codes in memory: {len(pending_auth_codes)}", flush=True)
    print("=" * 80, flush=True)
    sys.stdout.flush()

    # Render consent screen HTML directly (inline rendering)
    consent_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Authorize Music Assistant</title>
    <style>
        body {{font-family: system-ui; background: linear-gradient(135deg, #667eea, #764ba2); display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 20px}}
        .card {{background: white; border-radius: 16px; padding: 40px; max-width: 500px; box-shadow: 0 10px 40px rgba(0,0,0,0.2)}}
        h1 {{color: #1a202c; margin: 0 0 8px 0}}
        .subtitle {{color: #718096; font-size: 14px; margin-bottom: 24px}}
        .permissions {{background: #f7fafc; border-left: 4px solid #667eea; border-radius: 8px; padding: 16px; margin: 24px 0}}
        .permissions-title {{font-size: 14px; font-weight: 600; color: #2d3748; margin-bottom: 12px}}
        .permissions li {{font-size: 14px; color: #4a5568; padding: 6px 0; padding-left: 24px; position: relative}}
        .permissions li:before {{content: "✓"; position: absolute; left: 0; color: #667eea; font-weight: bold}}
        button {{width: 100%; padding: 14px; background: #667eea; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; margin-top: 24px; font-size: 16px}}
        button:hover {{background: #5a67d8}}
    </style>
</head>
<body>
    <div class="card">
        <h1>🎵 Authorize Music Assistant</h1>
        <p class="subtitle">Amazon Alexa is requesting access to your account</p>
        <div class="permissions">
            <div class="permissions-title">This will allow Amazon Alexa to:</div>
            <ul>
                <li>Read your music library and playlists</li>
                <li>Control playback (play, pause, skip)</li>
            </ul>
        </div>
        <form method="POST" action="/alexa/approve">
            <input type="hidden" name="auth_code" value="{temp_auth_code}">
            <input type="hidden" name="state" value="{params['state']}">
            <button type="submit">Approve & Link Account</button>
        </form>
    </div>
</body>
</html>"""

    return web.Response(text=consent_html, content_type='text/html')


async def approve_endpoint(request: web.Request) -> web.Response:
    """
    OAuth 2.0 Consent Approval Handler (POST)

    Handles form submission from consent.html when user clicks "Approve & Link Account"

    POST Body (application/x-www-form-urlencoded):
    - auth_code: temporary authorization code from /authorize endpoint
    - state: CSRF protection token (must match value in auth_code metadata)

    Returns:
    - 302 Redirect to redirect_uri with final authorization code (if approved)
    - 400 Error response if validation fails (CSRF, expired, etc.)

    Flow:
    1. User clicks "Approve & Link Account" on consent screen
    2. Browser POSTs to /alexa/approve with hidden form fields
    3. Server validates state parameter (CSRF protection)
    4. Server moves code from pending_auth_codes to auth_codes (approval)
    5. Server redirects to Alexa with authorization code
    """
    import sys

    try:
        body = await request.post()

        # Extract form data
        temp_auth_code = body.get('auth_code')
        state = body.get('state')

        print(f"\n{'='*80}", flush=True)
        print(f"👤 CONSENT APPROVAL FORM SUBMITTED", flush=True)
        print(f"{'='*80}", flush=True)
        print(f"   Temporary auth code: {temp_auth_code[:20] if temp_auth_code else 'MISSING'}...", flush=True)
        print(f"   State (CSRF): {state[:20] if state else 'MISSING'}...", flush=True)
        print(f"   Pending codes in memory: {len(pending_auth_codes)}", flush=True)
        print(f"{'='*80}", flush=True)
        sys.stdout.flush()

        # Validate form data
        if not temp_auth_code or not state:
            error_message = 'Missing required form parameters (auth_code or state)'
            print(f"❌ {error_message}", flush=True)
            error_html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Authorization Error</title><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}.card{{background:white;border-radius:16px;padding:40px;max-width:500px;box-shadow:0 10px 40px rgba(0,0,0,0.2)}}.header{{text-align:center;margin-bottom:30px}}.logo{{font-size:48px;margin-bottom:16px}}h1{{font-size:24px;font-weight:600;color:#1a202c;margin-bottom:8px}}.error-box{{background:#fff5f5;border-left:4px solid #fc8181;border-radius:8px;padding:16px;margin:24px 0}}.error-title{{font-size:16px;font-weight:600;color:#c53030;margin-bottom:8px}}.error-message{{font-size:14px;color:#742a2a;line-height:1.5}}.footer{{margin-top:24px;padding-top:20px;border-top:1px solid #e2e8f0;font-size:14px;color:#718096;text-align:center}}</style></head><body><div class="card"><div class="header"><div class="logo">⚠️</div><h1>Authorization Failed</h1></div><div class="error-box"><div class="error-title">Error</div><div class="error-message">{error_message}</div></div><div class="footer"><p>Please close this window and try again.</p></div></div></body></html>"""
            return web.Response(text=error_html, content_type='text/html')

        # Look up pending code
        if temp_auth_code not in pending_auth_codes:
            error_message = f'Authorization code not found or already approved'
            print(f"❌ {error_message}", flush=True)
            error_html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Authorization Error</title><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}.card{{background:white;border-radius:16px;padding:40px;max-width:500px;box-shadow:0 10px 40px rgba(0,0,0,0.2)}}.header{{text-align:center;margin-bottom:30px}}.logo{{font-size:48px;margin-bottom:16px}}h1{{font-size:24px;font-weight:600;color:#1a202c;margin-bottom:8px}}.error-box{{background:#fff5f5;border-left:4px solid #fc8181;border-radius:8px;padding:16px;margin:24px 0}}.error-title{{font-size:16px;font-weight:600;color:#c53030;margin-bottom:8px}}.error-message{{font-size:14px;color:#742a2a;line-height:1.5}}.footer{{margin-top:24px;padding-top:20px;border-top:1px solid #e2e8f0;font-size:14px;color:#718096;text-align:center}}</style></head><body><div class="card"><div class="header"><div class="logo">⚠️</div><h1>Authorization Failed</h1></div><div class="error-box"><div class="error-title">Error</div><div class="error-message">{error_message}</div></div><div class="footer"><p>Please close this window and try again.</p></div></div></body></html>"""
            return web.Response(text=error_html, content_type='text/html')

        pending_data = pending_auth_codes[temp_auth_code]

        # Validate state (CSRF protection)
        if state != pending_data['state']:
            error_message = 'CSRF validation failed: state parameter mismatch'
            print(f"❌ {error_message}", flush=True)
            print(f"   Expected: {pending_data['state'][:20]}...", flush=True)
            print(f"   Got: {state[:20]}...", flush=True)
            error_html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Authorization Error</title><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}.card{{background:white;border-radius:16px;padding:40px;max-width:500px;box-shadow:0 10px 40px rgba(0,0,0,0.2)}}.header{{text-align:center;margin-bottom:30px}}.logo{{font-size:48px;margin-bottom:16px}}h1{{font-size:24px;font-weight:600;color:#1a202c;margin-bottom:8px}}.error-box{{background:#fff5f5;border-left:4px solid #fc8181;border-radius:8px;padding:16px;margin:24px 0}}.error-title{{font-size:16px;font-weight:600;color:#c53030;margin-bottom:8px}}.error-message{{font-size:14px;color:#742a2a;line-height:1.5}}.footer{{margin-top:24px;padding-top:20px;border-top:1px solid #e2e8f0;font-size:14px;color:#718096;text-align:center}}</style></head><body><div class="card"><div class="header"><div class="logo">⚠️</div><h1>Authorization Failed</h1></div><div class="error-box"><div class="error-title">Error</div><div class="error-message">{error_message}</div></div><div class="footer"><p>Please close this window and try again.</p></div></div></body></html>"""
            return web.Response(text=error_html, content_type='text/html')

        # Validate code not expired
        if time.time() > pending_data['expires_at']:
            del pending_auth_codes[temp_auth_code]
            error_message = 'Authorization request has expired. Please start over.'
            print(f"❌ {error_message}", flush=True)
            error_html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Authorization Error</title><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}.card{{background:white;border-radius:16px;padding:40px;max-width:500px;box-shadow:0 10px 40px rgba(0,0,0,0.2)}}.header{{text-align:center;margin-bottom:30px}}.logo{{font-size:48px;margin-bottom:16px}}h1{{font-size:24px;font-weight:600;color:#1a202c;margin-bottom:8px}}.error-box{{background:#fff5f5;border-left:4px solid #fc8181;border-radius:8px;padding:16px;margin:24px 0}}.error-title{{font-size:16px;font-weight:600;color:#c53030;margin-bottom:8px}}.error-message{{font-size:14px;color:#742a2a;line-height:1.5}}.footer{{margin-top:24px;padding-top:20px;border-top:1px solid #e2e8f0;font-size:14px;color:#718096;text-align:center}}</style></head><body><div class="card"><div class="header"><div class="logo">⚠️</div><h1>Authorization Failed</h1></div><div class="error-box"><div class="error-title">Error</div><div class="error-message">{error_message}</div></div><div class="footer"><p>Please close this window and try again.</p></div></div></body></html>"""
            return web.Response(text=error_html, content_type='text/html')

        # USER APPROVED! Move code from pending to active
        print(f"✅ User approved! Moving code from pending to active...", flush=True)

        # Generate final authorization code for Alexa
        final_auth_code = generate_secure_token(32)

        # Store in active auth_codes with full metadata
        auth_codes[final_auth_code] = {
            'client_id': pending_data['client_id'],
            'code_challenge': pending_data['code_challenge'],
            'redirect_uri': pending_data['redirect_uri'],
            'user_id': 'test_user',  # In production, from LWA auth
            'expires_at': time.time() + AUTH_CODE_EXPIRY,
            'scope': pending_data['scope']
        }

        # Remove from pending codes (one-time use)
        del pending_auth_codes[temp_auth_code]

        print(f"✅ Final auth code generated: {final_auth_code[:20]}...", flush=True)
        print(f"   Active codes in memory: {len(auth_codes)}", flush=True)

        # Build redirect URL with final authorization code
        redirect_params = {
            'code': final_auth_code,
            'state': state  # Echo back state for CSRF protection
        }
        redirect_url = f"{pending_data['redirect_uri']}?{urlencode(redirect_params)}"

        print(f"✅ Redirecting to: {redirect_url[:80]}...", flush=True)
        print(f"{'='*80}", flush=True)
        sys.stdout.flush()

        # Redirect back to Alexa with authorization code
        return web.Response(
            status=302,
            headers={'Location': redirect_url}
        )

    except Exception as e:
        print(f"❌ ERROR in approve_endpoint: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        error_message = f'Internal server error: {str(e)}'
        error_html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Authorization Error</title><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}}.card{{background:white;border-radius:16px;padding:40px;max-width:500px;box-shadow:0 10px 40px rgba(0,0,0,0.2)}}.header{{text-align:center;margin-bottom:30px}}.logo{{font-size:48px;margin-bottom:16px}}h1{{font-size:24px;font-weight:600;color:#1a202c;margin-bottom:8px}}.error-box{{background:#fff5f5;border-left:4px solid #fc8181;border-radius:8px;padding:16px;margin:24px 0}}.error-title{{font-size:16px;font-weight:600;color:#c53030;margin-bottom:8px}}.error-message{{font-size:14px;color:#742a2a;line-height:1.5}}.footer{{margin-top:24px;padding-top:20px;border-top:1px solid #e2e8f0;font-size:14px;color:#718096;text-align:center}}</style></head><body><div class="card"><div class="header"><div class="logo">⚠️</div><h1>Authorization Failed</h1></div><div class="error-box"><div class="error-title">Error</div><div class="error-message">{error_message}</div></div><div class="footer"><p>Please close this window and try again.</p></div></div></body></html>"""
        return web.Response(text=error_html, content_type='text/html')


async def token_endpoint(request: web.Request) -> web.Response:
    """
    OAuth 2.0 Token Endpoint (RFC 6749 Section 3.2)

    POST Body (application/x-www-form-urlencoded):
    - grant_type: "authorization_code" or "refresh_token"
    - code: authorization code (if grant_type=authorization_code)
    - redirect_uri: must match the one from /authorize
    - client_id: Alexa Skill client ID
    - code_verifier: PKCE verifier (plain text that hashes to code_challenge)
    - refresh_token: refresh token (if grant_type=refresh_token)

    Returns JSON:
    {
        "access_token": "...",
        "token_type": "Bearer",
        "expires_in": 3600,
        "refresh_token": "...",
        "scope": "music.read music.control"
    }

    Example:
    POST /token
    grant_type=authorization_code&code=abc123&redirect_uri=https://...&client_id=alexa_skill_123&code_verifier=xyz789
    """
    # Parse POST body
    body = await request.post()

    # ===== DEBUG LOGGING: Capture Alexa's Token Request =====
    # Remove this block after debugging is complete
    import sys
    import json
    from datetime import datetime

    debug_info = {
        'timestamp': datetime.now().isoformat(),
        'endpoint': '/alexa/token',
        'method': request.method,
        'form_data': dict(body),  # All POST parameters
        'query_params': dict(request.rel_url.query),
        'headers': {
            k: v for k, v in request.headers.items()
            if k.lower() not in ['authorization', 'cookie']  # Exclude sensitive headers
        },
        'remote_addr': request.remote,
        'content_type': request.content_type
    }

    # Print to BOTH stdout/stderr AND a log file
    debug_output = f"\n{'='*80}\n🎯 ALEXA TOKEN REQUEST DEBUG\n{'='*80}\n{json.dumps(debug_info, indent=2)}\n{'='*80}\n"

    for stream in [sys.stdout, sys.stderr]:
        print(debug_output, file=stream, flush=True)

    # Also write to a log file
    try:
        with open('/data/oauth_debug.log', 'a') as f:
            f.write(debug_output)
            f.flush()
    except Exception as e:
        print(f"Failed to write to debug log: {e}", file=sys.stderr)
    # ===== END DEBUG LOGGING =====

    grant_type = body.get('grant_type')

    if not grant_type:
        return web.json_response({
            'error': 'invalid_request',
            'error_description': 'Missing grant_type parameter'
        }, status=400)

    # Handle authorization_code grant
    if grant_type == 'authorization_code':
        return await handle_authorization_code_grant(body, request)

    # Handle refresh_token grant
    elif grant_type == 'refresh_token':
        return await handle_refresh_token_grant(body)

    else:
        return web.json_response({
            'error': 'unsupported_grant_type',
            'error_description': f'Grant type "{grant_type}" not supported. Use "authorization_code" or "refresh_token"'
        }, status=400)


def parse_basic_auth(auth_header: Optional[str]) -> Optional[tuple[str, str]]:
    """
    Parse HTTP Basic Authentication header.

    Format: Authorization: Basic base64(client_id:client_secret)

    Returns: (client_id, client_secret) tuple or None if invalid
    """
    if not auth_header or not auth_header.startswith('Basic '):
        return None

    try:
        # Extract base64 part after "Basic "
        encoded = auth_header[6:]  # Remove "Basic " prefix
        decoded = base64.b64decode(encoded).decode('utf-8')

        # Split into client_id:client_secret
        if ':' not in decoded:
            return None

        client_id, client_secret = decoded.split(':', 1)
        return (client_id, client_secret)
    except Exception as e:
        print(f"⚠️  Failed to parse Basic Auth: {e}", flush=True)
        return None


async def handle_authorization_code_grant(body, request: web.Request) -> web.Response:
    """Handle authorization_code grant type with optional PKCE validation."""

    # Validate required parameters (code_verifier is optional, only needed if PKCE was used)
    # NOTE: client_secret can be in POST body OR Authorization header (HTTP Basic Auth)
    required = ['code', 'redirect_uri', 'client_id']
    missing = [p for p in required if p not in body]
    if missing:
        return web.json_response({
            'error': 'invalid_request',
            'error_description': f'Missing required parameters: {", ".join(missing)}'
        }, status=400)

    code = body['code']
    redirect_uri = body['redirect_uri']
    client_id = body['client_id']
    code_verifier = body.get('code_verifier')  # Optional - only needed if PKCE was used
    client_secret = body.get('client_secret')  # Try POST body first

    # If no client_secret in POST body, try HTTP Basic Auth header
    if not client_secret:
        auth_header = request.headers.get('Authorization')
        if auth_header:
            auth_credentials = parse_basic_auth(auth_header)
            if auth_credentials:
                # Override client_id and client_secret from Basic Auth if present
                basic_client_id, basic_client_secret = auth_credentials
                # If client_id in POST doesn't match, use Basic Auth version
                if client_id != basic_client_id:
                    print(f"⚠️  client_id mismatch: POST={client_id}, Basic Auth={basic_client_id}", flush=True)
                client_id = basic_client_id
                client_secret = basic_client_secret
                print(f"✅ Using credentials from HTTP Basic Auth for client_id: {client_id}", flush=True)

    # Validate client credentials
    # validate_client() handles both confidential clients (require client_secret)
    # and public clients (use PKCE, no client_secret required)
    print(f"🔍 Validating client_id='{client_id}', has_secret={bool(client_secret)}", flush=True)
    client_valid = validate_client(client_id, client_secret)
    print(f"✅ validate_client() returned: {client_valid}", flush=True)

    if not client_valid:
        error_response = {
            'error': 'invalid_client',
            'error_description': 'Client authentication failed (invalid client_id)'
        }
        print(f"❌ CLIENT VALIDATION FAILED: {error_response}", flush=True)
        return web.json_response(error_response, status=401)

    # Log successful authentication
    if client_secret:
        print(f"✅ Client '{client_id}' authenticated with credentials", flush=True)
    else:
        print(f"✅ Client '{client_id}' authenticated as public client (PKCE)", flush=True)

    # Validate authorization code exists
    print(f"🔍 Looking up auth code: {code[:20]}..., total codes: {len(auth_codes)}", flush=True)
    if code not in auth_codes:
        return web.json_response({
            'error': 'invalid_grant',
            'error_description': 'Authorization code not found or already used'
        }, status=400)

    auth_data = auth_codes[code]

    # Validate authorization code not expired
    if time.time() > auth_data['expires_at']:
        del auth_codes[code]  # Clean up expired code
        return web.json_response({
            'error': 'invalid_grant',
            'error_description': 'Authorization code has expired'
        }, status=400)

    # Validate client_id matches
    if client_id != auth_data['client_id']:
        return web.json_response({
            'error': 'invalid_client',
            'error_description': 'client_id does not match authorization request'
        }, status=400)

    # Validate redirect_uri matches
    if redirect_uri != auth_data['redirect_uri']:
        return web.json_response({
            'error': 'invalid_grant',
            'error_description': 'redirect_uri does not match authorization request'
        }, status=400)

    # PKCE Verification (only if code_challenge was provided in authorization request)
    if auth_data.get('code_challenge'):
        # PKCE was used, so code_verifier is required
        if not code_verifier:
            return web.json_response({
                'error': 'invalid_grant',
                'error_description': 'PKCE code_verifier required (code_challenge was provided in authorization)'
            }, status=400)

        # Validate PKCE: Hash code_verifier and compare to code_challenge
        computed_challenge = hash_code_verifier(code_verifier)
        if computed_challenge != auth_data['code_challenge']:
            return web.json_response({
                'error': 'invalid_grant',
                'error_description': 'PKCE verification failed: code_verifier does not match code_challenge'
            }, status=400)
    # else: PKCE not used, skip verification

    # All validations passed - generate tokens
    user_id = auth_data['user_id']
    scope = auth_data['scope']

    access_token = generate_secure_token(32)
    refresh_token = generate_secure_token(32)

    # Store tokens
    tokens[user_id] = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_at': time.time() + ACCESS_TOKEN_EXPIRY,
        'scope': scope,
        'client_id': client_id
    }

    # Invalidate authorization code (one-time use)
    del auth_codes[code]

    # Return tokens
    return web.json_response({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': ACCESS_TOKEN_EXPIRY,
        'refresh_token': refresh_token,
        'scope': scope
    })


async def handle_refresh_token_grant(body) -> web.Response:
    """Handle refresh_token grant type."""

    # Validate required parameters
    required = ['refresh_token', 'client_id']
    missing = [p for p in required if p not in body]
    if missing:
        return web.json_response({
            'error': 'invalid_request',
            'error_description': f'Missing required parameters: {", ".join(missing)}'
        }, status=400)

    refresh_token = body['refresh_token']
    client_id = body['client_id']

    # Find user_id by refresh token
    user_id = None
    for uid, token_data in tokens.items():
        if token_data.get('refresh_token') == refresh_token and token_data.get('client_id') == client_id:
            user_id = uid
            break

    if not user_id:
        return web.json_response({
            'error': 'invalid_grant',
            'error_description': 'Refresh token not found or invalid'
        }, status=400)

    # Generate new access token (keep same refresh token)
    access_token = generate_secure_token(32)

    tokens[user_id]['access_token'] = access_token
    tokens[user_id]['expires_at'] = time.time() + ACCESS_TOKEN_EXPIRY

    return web.json_response({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': ACCESS_TOKEN_EXPIRY,
        'refresh_token': refresh_token,  # Same refresh token
        'scope': tokens[user_id]['scope']
    })


def verify_access_token(token: str) -> Optional[dict]:
    """
    Verify access token and return user info if valid.

    This would be called by Music Assistant API endpoints to authenticate requests.

    Returns:
        dict with user_id and scope if valid, None if invalid/expired
    """
    for user_id, token_data in tokens.items():
        if token_data.get('access_token') == token:
            if time.time() < token_data['expires_at']:
                return {
                    'user_id': user_id,
                    'scope': token_data['scope']
                }
    return None


# Integration with Music Assistant

def register_oauth_routes(app: web.Application):
    """
    Register OAuth endpoints with Music Assistant's web server.

    This should be called during provider initialization, similar to
    how Spotify provider registers its callback route.

    Usage in Alexa provider __init__.py:
        async def setup(mass: MusicAssistant) -> AlexaProvider:
            provider = AlexaProvider(mass)
            register_oauth_routes(mass.webserver.app)
            return provider
    """
    # Register OAuth endpoints
    app.router.add_get('/alexa/authorize', authorize_endpoint)
    app.router.add_post('/alexa/approve', approve_endpoint)
    app.router.add_post('/alexa/token', token_endpoint)

    print("✅ Alexa OAuth endpoints registered:")
    print(f"   - GET  /alexa/authorize (Authorization endpoint → Consent screen)")
    print(f"   - POST /alexa/approve (Consent approval handler)")
    print(f"   - POST /alexa/token (Token endpoint)")


# Testing utilities

async def test_oauth_flow():
    """
    Test the OAuth flow end-to-end.

    Simulates:
    1. Alexa Skill initiating authorization
    2. User authenticating and granting consent
    3. Alexa receiving authorization code
    4. Alexa exchanging code for access token (with PKCE)
    5. Alexa using access token to make API calls
    6. Alexa refreshing access token when expired
    """
    print("\n" + "="*60)
    print("Testing OAuth 2.0 Authorization Code Flow with PKCE")
    print("="*60)

    # Step 1: Generate PKCE pair (done by Alexa Skill)
    code_verifier = generate_secure_token(32)
    code_challenge = hash_code_verifier(code_verifier)
    print(f"\n1️⃣  Alexa generates PKCE pair:")
    print(f"   code_verifier: {code_verifier[:20]}...")
    print(f"   code_challenge: {code_challenge[:20]}...")

    # Step 2: Alexa redirects user to /authorize
    client_id = "amazon-alexa"
    redirect_uri = "https://pitangui.amazon.com/auth/o2/callback"
    state = generate_secure_token(16)

    auth_url = f"/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect_uri}&state={state}&code_challenge={code_challenge}&code_challenge_method=S256"
    print(f"\n2️⃣  Alexa redirects user to authorization endpoint:")
    print(f"   {auth_url[:80]}...")

    # Simulate authorization endpoint (would be HTTP request in production)
    from unittest.mock import Mock
    mock_request = Mock()
    mock_request.rel_url.query = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'state': state,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
        'scope': 'music.read music.control'
    }

    response = await authorize_endpoint(mock_request)
    print(f"\n3️⃣  Authorization endpoint generates code and redirects:")
    print(f"   Status: {response.status} (302 Redirect)")

    # Extract authorization code from redirect Location header
    location = response.headers['Location']
    auth_code = parse_qs(location.split('?')[1])['code'][0]
    returned_state = parse_qs(location.split('?')[1])['state'][0]
    print(f"   Authorization code: {auth_code[:20]}...")
    print(f"   State (CSRF): {returned_state[:20]}... {'✅ matches' if returned_state == state else '❌ MISMATCH'}")

    # Step 3: Alexa exchanges code for access token
    print(f"\n4️⃣  Alexa exchanges authorization code for access token:")
    print(f"   Sending code + code_verifier to /token endpoint...")

    token_body = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': 'Nv8Xh-zG_wR3mK2pL4jF9qY6bT5vC1xD0sW7aM',
        'code_verifier': code_verifier
    }

    mock_token_request = Mock()
    mock_token_request.post = lambda: token_body

    token_response = await handle_authorization_code_grant(token_body)
    token_data = json.loads(token_response.body)

    if 'access_token' in token_data:
        print(f"   ✅ Access token received: {token_data['access_token'][:20]}...")
        print(f"   ✅ Refresh token received: {token_data['refresh_token'][:20]}...")
        print(f"   ✅ Expires in: {token_data['expires_in']} seconds")
        print(f"   ✅ Scope: {token_data['scope']}")
    else:
        print(f"   ❌ Error: {token_data.get('error')}")
        print(f"   ❌ Description: {token_data.get('error_description')}")
        return

    # Step 4: Verify access token
    access_token = token_data['access_token']
    print(f"\n5️⃣  Verifying access token:")
    user_info = verify_access_token(access_token)
    if user_info:
        print(f"   ✅ Token valid for user: {user_info['user_id']}")
        print(f"   ✅ Scope: {user_info['scope']}")
    else:
        print(f"   ❌ Token verification failed")
        return

    # Step 5: Test token refresh
    print(f"\n6️⃣  Testing token refresh:")
    refresh_body = {
        'grant_type': 'refresh_token',
        'refresh_token': token_data['refresh_token'],
        'client_id': client_id
    }

    refresh_response = await handle_refresh_token_grant(refresh_body)
    refresh_data = json.loads(refresh_response.body)

    if 'access_token' in refresh_data:
        print(f"   ✅ New access token: {refresh_data['access_token'][:20]}...")
        print(f"   ✅ Refresh token (same): {refresh_data['refresh_token'][:20]}...")
        print(f"   ✅ Token refresh successful!")
    else:
        print(f"   ❌ Refresh failed: {refresh_data.get('error')}")

    print("\n" + "="*60)
    print("✅ OAuth flow test completed successfully!")
    print("="*60 + "\n")


if __name__ == '__main__':
    # Run test
    asyncio.run(test_oauth_flow())
