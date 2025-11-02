#!/usr/bin/env python3
"""Nuclear reset - Remove Apple Music provider from settings"""

import json
import sys

print("🚨 NUCLEAR RESET: Removing Apple Music Provider")
print("=" * 60)

try:
    # Read current settings
    with open('/data/settings.json', 'r') as f:
        settings = json.load(f)

    # Check if Apple Music provider exists
    providers = settings.get('music_providers', {})
    apple_key = 'apple_music--R9eXqpej'

    if apple_key in providers:
        print(f"✅ Found provider: {apple_key}")
        print(f"   Instance ID: {providers[apple_key].get('instance_id')}")
        print(f"   Enabled: {providers[apple_key].get('enabled')}")

        # Remove the provider
        del providers[apple_key]
        settings['music_providers'] = providers

        # Write back
        with open('/data/settings.json', 'w') as f:
            json.dump(settings, f, indent=2)

        print(f"✅ Provider removed successfully")
        print(f"✅ Settings saved")
        sys.exit(0)
    else:
        print(f"⚠️ Provider {apple_key} not found in settings")
        print(f"Available providers: {list(providers.keys())}")
        sys.exit(1)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)