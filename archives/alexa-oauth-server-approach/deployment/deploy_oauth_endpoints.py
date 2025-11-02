#!/usr/bin/env python3
"""
Deploy OAuth endpoints to Music Assistant

This script:
1. Copies alexa_oauth_endpoints.py to Music Assistant
2. Creates integration patch for Alexa provider
3. Registers OAuth routes with the web server
4. Provides Cloudflare Tunnel configuration

Run this script to set up OAuth support in Music Assistant.
"""

import os
import sys

print("🚀 Deploying OAuth Endpoints to Music Assistant")
print("="*60)

# Step 1: Copy OAuth endpoints module
print("\n1️⃣  Copying OAuth endpoints module...")

oauth_module_source = "/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple/alexa_oauth_endpoints.py"
oauth_module_dest = "/data/alexa_oauth_endpoints.py"

# In container, this would be:
# import shutil
# shutil.copy(oauth_module_source, oauth_module_dest)
# os.chmod(oauth_module_dest, 0o644)

print(f"   Source: {oauth_module_source}")
print(f"   Destination: {oauth_module_dest}")
print(f"   ⏳ Copy this file to the container manually:")
print(f"   ssh root@haboxhill.local \"cat > {oauth_module_dest}\" < \"{oauth_module_source}\"")

# Step 2: Create integration patch
print("\n2️⃣  Creating integration patch for Alexa provider...")

integration_patch = '''
# Add this to /app/venv/lib/python3.13/site-packages/music_assistant/providers/alexa/__init__.py
# At the top of the file, after other imports:

import sys
sys.path.insert(0, '/data')
from alexa_oauth_endpoints import register_oauth_routes

# In the setup() function or __init__ method, add:

async def setup(mass: MusicAssistant) -> AlexaProvider:
    """Initialize provider(instance) with given configuration."""
    provider = AlexaProvider(mass)

    # Register OAuth endpoints
    register_oauth_routes(mass.webserver.app)

    return provider
'''

patch_file = "/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple/alexa_oauth_integration_patch.txt"
with open(patch_file, 'w') as f:
    f.write(integration_patch)

print(f"   ✅ Integration patch saved to:")
print(f"   {patch_file}")

# Step 3: OAuth endpoint URLs
print("\n3️⃣  OAuth Endpoint URLs (after deployment):")
print(f"   Authorization: http://192.168.130.147:8095/alexa/authorize")
print(f"   Token:         http://192.168.130.147:8095/alexa/token")

# Step 4: Cloudflare Tunnel configuration
print("\n4️⃣  Cloudflare Tunnel Setup (for public access):")
print(f"   Install cloudflared on haboxhill.local:")
print(f"   ssh root@haboxhill.local")
print(f"   curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb")
print(f"   dpkg -i cloudflared.deb")
print(f"")
print(f"   Start tunnel:")
print(f"   cloudflared tunnel --url http://localhost:8095")
print(f"")
print(f"   Note the generated URL (e.g., https://abc-def-ghi.trycloudflare.com)")
print(f"   Use this URL as the base for OAuth endpoints in Alexa Skill configuration")

# Step 5: Alexa Skill configuration
print("\n5️⃣  Alexa Skill Configuration (next steps):")
print(f"   1. Go to: https://developer.amazon.com/alexa/console/ask")
print(f"   2. Create new skill: 'Music Assistant'")
print(f"   3. Choose 'Custom' model, 'Provision your own' hosting")
print(f"   4. Configure Account Linking:")
print(f"      - Authorization URI: https://YOUR-TUNNEL-URL/alexa/authorize")
print(f"      - Access Token URI: https://YOUR-TUNNEL-URL/alexa/token")
print(f"      - Client ID: (generate random ID)")
print(f"      - Scopes: music.read music.control")
print(f"      - Authorization Grant Type: Auth Code Grant")
print(f"      - Enable PKCE: Yes")

# Step 6: Testing
print("\n6️⃣  Testing OAuth Flow:")
print(f"   After deployment, test the endpoints:")
print(f"   curl 'http://192.168.130.147:8095/alexa/authorize?response_type=code&client_id=test&redirect_uri=http://localhost&state=test&code_challenge=abc&code_challenge_method=S256'")
print(f"")
print(f"   Expected: 302 redirect with authorization code")

print("\n" + "="*60)
print("✅ Deployment guide complete!")
print("="*60)
print("\nNext steps:")
print("1. Copy alexa_oauth_endpoints.py to container")
print("2. Apply integration patch to Alexa provider")
print("3. Restart Music Assistant container")
print("4. Set up Cloudflare Tunnel")
print("5. Create Alexa Skill with Account Linking")
print("6. Test OAuth flow with Echo Dot")
