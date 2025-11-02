#!/bin/bash
# Real-Time OAuth Log Monitor for Account Linking Test
# Run this in a separate terminal WHILE performing account linking in Alexa app

echo "=== OAuth Server Real-Time Log Monitor ==="
echo ""
echo "This will monitor OAuth server logs in real-time."
echo "Keep this running while you perform account linking in the Alexa app."
echo ""
echo "Expected log sequence during successful account linking:"
echo "  1. [INFO] GET /authorize - Authorization request from Alexa"
echo "  2. [INFO] Authorization code generated: XXXX"
echo "  3. [INFO] Redirecting to Alexa redirect_uri with code"
echo "  4. [INFO] POST /token - Token exchange request from Alexa"
echo "  5. [INFO] Client credentials validated: alexa-music-assistant"
echo "  6. [INFO] Access token generated for user: test_user"
echo "  7. [INFO] Refresh token generated: XXXX"
echo "  8. [INFO] Token response sent successfully"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo ""
echo "=========================================="
echo ""

# Follow logs with color highlighting for key events
docker logs -f oauth-server 2>&1 | while IFS= read -r line; do
    # Color-code different log levels and events
    if echo "$line" | grep -q "ERROR"; then
        echo -e "\033[0;31m$line\033[0m"  # Red for errors
    elif echo "$line" | grep -q "/authorize"; then
        echo -e "\033[0;32m$line\033[0m"  # Green for authorization requests
    elif echo "$line" | grep -q "/token"; then
        echo -e "\033[0;34m$line\033[0m"  # Blue for token requests
    elif echo "$line" | grep -q "generated\|created"; then
        echo -e "\033[1;33m$line\033[0m"  # Yellow for token generation
    elif echo "$line" | grep -q "Redirecting\|redirect"; then
        echo -e "\033[0;35m$line\033[0m"  # Magenta for redirects
    else
        echo "$line"
    fi
done
