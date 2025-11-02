#!/bin/bash
# Pre-Test Server Health Check for OAuth Account Linking
# Run this BEFORE attempting account linking in Alexa app

set -e

echo "=== Phase 2 Pre-Test Server Health Check ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Check if OAuth container is running
echo "1. Checking OAuth container status..."
CONTAINER_STATUS=$(docker ps --filter "name=oauth-server" --format "{{.Status}}" 2>/dev/null || echo "")
if [ -z "$CONTAINER_STATUS" ]; then
    echo -e "${RED}✗ OAuth container is NOT running${NC}"
    echo "Start it with: docker start oauth-server"
    exit 1
else
    echo -e "${GREEN}✓ OAuth container is running: $CONTAINER_STATUS${NC}"
fi
echo ""

# 2. Check local OAuth server response
echo "2. Checking local OAuth server (http://localhost:8099)..."
LOCAL_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8099/health 2>/dev/null || echo "000")
if [ "$LOCAL_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✓ Local OAuth server responding (HTTP $LOCAL_RESPONSE)${NC}"
else
    echo -e "${RED}✗ Local OAuth server not responding (HTTP $LOCAL_RESPONSE)${NC}"
    exit 1
fi
echo ""

# 3. Check Tailscale Funnel status
echo "3. Checking Tailscale Funnel status..."
FUNNEL_STATUS=$(tailscale funnel status 2>/dev/null || echo "ERROR")
if echo "$FUNNEL_STATUS" | grep -q "https://"; then
    FUNNEL_URL=$(echo "$FUNNEL_STATUS" | grep -o 'https://[^ ]*' | head -1)
    echo -e "${GREEN}✓ Tailscale Funnel is active${NC}"
    echo "  URL: $FUNNEL_URL"
else
    echo -e "${RED}✗ Tailscale Funnel is NOT active${NC}"
    echo "Start it with: tailscale funnel --bg --https=443 8099"
    exit 1
fi
echo ""

# 4. Check HTTPS endpoint (Tailscale Funnel)
echo "4. Checking public HTTPS endpoint..."
if [ -n "$FUNNEL_URL" ]; then
    HTTPS_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" "${FUNNEL_URL}/health" 2>/dev/null || echo "000")
    if [ "$HTTPS_RESPONSE" = "200" ]; then
        echo -e "${GREEN}✓ Public HTTPS endpoint responding (HTTP $HTTPS_RESPONSE)${NC}"
    else
        echo -e "${YELLOW}⚠ Public HTTPS endpoint issue (HTTP $HTTPS_RESPONSE)${NC}"
        echo "  This may be a temporary Tailscale issue - try again"
    fi
else
    echo -e "${YELLOW}⚠ Cannot test HTTPS endpoint - Funnel URL not found${NC}"
fi
echo ""

# 5. Check SSL certificate (via openssl)
echo "5. Checking SSL certificate..."
if [ -n "$FUNNEL_URL" ]; then
    HOSTNAME=$(echo "$FUNNEL_URL" | sed 's|https://||' | sed 's|/.*||')
    CERT_INFO=$(echo | openssl s_client -servername "$HOSTNAME" -connect "$HOSTNAME:443" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "")
    if [ -n "$CERT_INFO" ]; then
        echo -e "${GREEN}✓ SSL certificate is valid${NC}"
        echo "$CERT_INFO" | sed 's/^/  /'
    else
        echo -e "${YELLOW}⚠ Could not verify SSL certificate${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Cannot check SSL certificate - Funnel URL not found${NC}"
fi
echo ""

# 6. Display OAuth endpoints for reference
echo "6. OAuth Endpoints Ready for Testing:"
if [ -n "$FUNNEL_URL" ]; then
    echo -e "  ${GREEN}Authorization Endpoint:${NC} ${FUNNEL_URL}/authorize"
    echo -e "  ${GREEN}Token Endpoint:${NC} ${FUNNEL_URL}/token"
    echo -e "  ${GREEN}Health Check:${NC} ${FUNNEL_URL}/health"
fi
echo ""

# 7. Display Alexa Skill configuration reminder
echo "7. Alexa Skill Configuration Checklist:"
echo "  [ ] Account Linking enabled in Alexa Developer Console"
echo "  [ ] Authorization URI: ${FUNNEL_URL}/authorize"
echo "  [ ] Token URI: ${FUNNEL_URL}/token"
echo "  [ ] Client ID: alexa-music-assistant"
echo "  [ ] Client Secret: configured"
echo "  [ ] Scope: read (optional)"
echo ""

echo -e "${GREEN}=== Pre-Test Health Check Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Run the log monitor in a separate terminal:"
echo "   bash validation/phase2_log_monitor.sh"
echo "2. Open Alexa app and attempt account linking"
echo "3. Watch logs for real-time validation"
echo ""
