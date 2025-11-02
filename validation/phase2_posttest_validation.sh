#!/bin/bash
# Post-Test Validation for Account Linking
# Run this AFTER attempting account linking to verify tokens were generated

set -e

echo "=== Phase 2 Post-Test Validation ==="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 1. Check recent logs for success indicators
echo "1. Checking logs for successful account linking..."
RECENT_LOGS=$(docker logs --tail 50 oauth-server 2>&1)

if echo "$RECENT_LOGS" | grep -q "Authorization code generated"; then
    echo -e "${GREEN}✓ Authorization code was generated${NC}"
    AUTH_CODE=$(echo "$RECENT_LOGS" | grep "Authorization code generated" | tail -1 | sed 's/.*: //')
    echo "  Code: $AUTH_CODE"
else
    echo -e "${RED}✗ No authorization code found in logs${NC}"
    echo "  This means the /authorize endpoint was never called or failed"
fi
echo ""

if echo "$RECENT_LOGS" | grep -q "Redirecting to"; then
    echo -e "${GREEN}✓ Redirect to Alexa was sent${NC}"
    REDIRECT_URL=$(echo "$RECENT_LOGS" | grep "Redirecting to" | tail -1 | sed 's/.*: //')
    echo "  Redirect: $REDIRECT_URL"
else
    echo -e "${RED}✗ No redirect found in logs${NC}"
fi
echo ""

if echo "$RECENT_LOGS" | grep -q "POST /token"; then
    echo -e "${GREEN}✓ Token exchange request was received${NC}"
else
    echo -e "${YELLOW}⚠ No token exchange request found${NC}"
    echo "  This means Alexa may not have completed the flow"
fi
echo ""

if echo "$RECENT_LOGS" | grep -q "Access token generated"; then
    echo -e "${GREEN}✓ Access token was generated${NC}"
    ACCESS_TOKEN=$(echo "$RECENT_LOGS" | grep "Access token generated" | tail -1 | sed 's/.*: //')
    echo "  Token (first 50 chars): ${ACCESS_TOKEN:0:50}..."
else
    echo -e "${RED}✗ No access token generated${NC}"
fi
echo ""

if echo "$RECENT_LOGS" | grep -q "Refresh token generated"; then
    echo -e "${GREEN}✓ Refresh token was generated${NC}"
    REFRESH_TOKEN=$(echo "$RECENT_LOGS" | grep "Refresh token generated" | tail -1 | sed 's/.*: //')
    echo "  Token (first 30 chars): ${REFRESH_TOKEN:0:30}..."
else
    echo -e "${RED}✗ No refresh token generated${NC}"
fi
echo ""

if echo "$RECENT_LOGS" | grep -q "Token response sent successfully"; then
    echo -e "${GREEN}✓ Token response was sent to Alexa${NC}"
else
    echo -e "${RED}✗ Token response was not sent${NC}"
fi
echo ""

# 2. Check for errors
echo "2. Checking for errors in logs..."
ERROR_COUNT=$(echo "$RECENT_LOGS" | grep -c "ERROR" || true)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✓ No errors found in recent logs${NC}"
else
    echo -e "${RED}✗ Found $ERROR_COUNT error(s) in recent logs:${NC}"
    echo "$RECENT_LOGS" | grep "ERROR" | sed 's/^/  /'
fi
echo ""

# 3. Display full OAuth flow timeline
echo "3. OAuth Flow Timeline (last 50 log entries):"
echo "$RECENT_LOGS" | grep -E "(GET /authorize|Authorization code|Redirecting|POST /token|Access token|Refresh token|Token response)" | sed 's/^/  /'
echo ""

# 4. Suggest next steps based on results
echo "4. Next Steps:"
echo ""

if echo "$RECENT_LOGS" | grep -q "Token response sent successfully"; then
    echo -e "${GREEN}SUCCESS! Account linking appears to have completed.${NC}"
    echo ""
    echo "Verify in Alexa app:"
    echo "  1. Open Alexa app on your phone"
    echo "  2. Go to More > Skills & Games > Your Skills"
    echo "  3. Find 'Music Assistant' skill"
    echo "  4. Check if it shows 'Linked' or 'Link Account'"
    echo ""
    echo "Test the skill:"
    echo "  1. Say: 'Alexa, open Music Assistant'"
    echo "  2. Say: 'Play some music'"
    echo "  3. Check logs with: bash validation/phase2_log_monitor.sh"
    echo ""
elif echo "$RECENT_LOGS" | grep -q "Authorization code generated"; then
    echo -e "${YELLOW}PARTIAL SUCCESS - Authorization code generated but token exchange incomplete${NC}"
    echo ""
    echo "Possible causes:"
    echo "  - Alexa didn't complete the redirect (check Alexa app)"
    echo "  - Network issue between Alexa and your server"
    echo "  - Client secret mismatch in Alexa Developer Console"
    echo ""
    echo "Try:"
    echo "  1. Check Alexa app - does it show 'Linked' or error message?"
    echo "  2. Try account linking again"
    echo "  3. Verify Client Secret in Alexa Developer Console"
    echo ""
else
    echo -e "${RED}FAILED - Authorization endpoint was not called${NC}"
    echo ""
    echo "Possible causes:"
    echo "  - Alexa skill not configured with correct Authorization URI"
    echo "  - Tailscale Funnel not accessible from internet"
    echo "  - Alexa app showing error before reaching OAuth server"
    echo ""
    echo "Try:"
    echo "  1. Re-run pre-test health check: bash validation/phase2_pretest_check.sh"
    echo "  2. Verify Authorization URI in Alexa Developer Console"
    echo "  3. Test Funnel URL in browser: curl -I https://your-funnel-url/health"
    echo "  4. Check Alexa Developer Console for error messages"
    echo ""
fi

echo "For detailed diagnostics, run:"
echo "  bash validation/phase2_diagnostics.sh"
echo ""
