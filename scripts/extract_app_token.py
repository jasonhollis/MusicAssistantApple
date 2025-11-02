#!/usr/bin/env python3
"""Extract the MUSIC_APP_TOKEN from the obfuscated app_vars."""

import sys
import os

# Add the server path to sys.path
sys.path.insert(0, '/Users/jason/Library/Mobile Documents/com~apple~CloudDocs/Claude Stuff/projects/MusicAssistantApple/server-2.6.0')

try:
    from music_assistant.helpers.app_vars import app_var

    # Get the app token (index 8)
    app_token = app_var(8)

    print("Successfully extracted MUSIC_APP_TOKEN:")
    print(f"Token: {app_token}")
    print(f"Token length: {len(app_token)}")
    print(f"Token preview: {app_token[:50]}..." if len(app_token) > 50 else f"Token: {app_token}")

    # Check if it looks like a JWT
    if app_token.startswith("eyJ"):
        print("✓ Token appears to be a valid JWT (starts with 'eyJ')")
    else:
        print("⚠️  Warning: Token doesn't look like a JWT")

except ImportError as e:
    print(f"Failed to import app_vars: {e}")
    print("\nTrying alternative extraction method...")

    # Try to decode the obfuscated data directly
    import base64

    # The encoded string from app_vars.py
    encoded = '3YTNyUDOyQTOacb2=EmN5M2YjdzMhljYzYzYhlDMmFGNlVTOmNDZwMzNxYzNacb2=UDMzEGOyADO1QWO5kDNygTMlJGN5QzNzIWOmZTOiVmMacb2yMTNzITNacb2=UDZhJmMldTZ3QTY4IjZ3kTNxYjN0czNwI2YxkTM5MjNacb2==QMh5WOmZnewM2d4UDblRzZacb20QzMwAjNacb2=QzNiRTO3EjMjFzMldjY3QTMwEDMwADMiNWZ5UWO3UWMacb2n9FRIpWRJJmaX1meRNTcoN3X5UmZ0pnVwQ2Tk1SZZxUUkN1NHpndHVXc5pWY0N2R2A1NDh2Vw50aQVHTkhXO0NETtJ0YStUQqxGTTxEZ0UDc58lYrdlL5wGRPVTTU9UNBpmTzUkaPlWQIVGbKNET1cGVPhXUE5UMRpnT49maJBjRXFWa3lWS51kRVVFZqZFMBFjUSpUaPlWTzMGcKlXZuElZpFVMWtkSp9UaBhVZwo0QMlWU6VFTSRUVWZFVPFFZqlkNJNkWwRXbJNXSp5UMJpXVGpUaPl2YHJGaKlXZacb2==QVnRlQFFHa5sEckJ1UEJkNacb2=0DOHRla6N3YJZjTxFUVlhmTWFTYrh2czkTUjFETilUS5oFci52NZ1GU1VGe'

    # Split by 'acb2' and get the 8th element (index 8)
    parts = encoded.split('acb2')
    if len(parts) > 8:
        token_part = parts[8][::-1]  # Reverse the string
        try:
            decoded = base64.b64decode(token_part).decode()
            print(f"Extracted token: {decoded[:50]}...")
        except:
            print("Failed to decode token part")

except Exception as e:
    print(f"Error: {e}")