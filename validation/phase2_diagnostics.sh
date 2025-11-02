#!/bin/bash
# Detailed Diagnostics for Failed Account Linking
# Run this if account linking fails to identify the root cause

set -e

echo "=== Phase 2 Account Linking Diagnostics ==="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get recent logs
RECENT_LOGS=$(docker logs --tail 100 oauth-server 2>&1)

echo -e "${CYAN}=== DIAGNOSTIC CHECKLIST ===${NC}"
echo ""

# Diagnostic 1: Was /authorize endpoint called?
echo -e "${BLUE}1. Authorization Request (Step 1 of OAuth flow)${NC}"
if echo "$RECENT_LOGS" | grep -q "GET /authorize"; then
    echo -e "${GREEN}✓ /authorize endpoint WAS called${NC}"
    echo ""
    echo "Last authorization request:"
    echo "$RECENT_LOGS" | grep "GET /authorize" | tail -1 | sed 's/^/  /'
    echo ""

    # Check query parameters
    if echo "$RECENT_LOGS" | grep -q "client_id"; then
        CLIENT_ID=$(echo "$RECENT_LOGS" | grep "client_id" | tail -1 | sed 's/.*client_id[=:] *//' | awk '{print $1}' | sed 's/[,&].*//')
        echo "  Client ID: $CLIENT_ID"
        if [ "$CLIENT_ID" = "alexa-music-assistant" ]; then
            echo -e "  ${GREEN}✓ Correct client ID${NC}"
        else
            echo -e "  ${RED}✗ Wrong client ID (expected: alexa-music-assistant)${NC}"
        fi
    fi
    echo ""
else
    echo -e "${RED}✗ /authorize endpoint was NEVER called${NC}"
    echo ""
    echo -e "${YELLOW}ROOT CAUSE: Alexa never reached your OAuth server${NC}"
    echo ""
    echo "Possible reasons:"
    echo "  1. Authorization URI in Alexa Developer Console is wrong"
    echo "  2. Tailscale Funnel is not running or not accessible"
    echo "  3. Firewall blocking Alexa's servers"
    echo "  4. DNS issue preventing Alexa from resolving Funnel URL"
    echo ""
    echo "Action Items:"
    echo "  [ ] Verify Authorization URI in Alexa Developer Console"
    echo "  [ ] Test Funnel URL in browser from different network"
    echo "  [ ] Run: tailscale funnel status"
    echo "  [ ] Check if Funnel URL resolves: nslookup <your-funnel-domain>"
    echo ""
    exit 1
fi

# Diagnostic 2: Was authorization code generated?
echo -e "${BLUE}2. Authorization Code Generation (Step 2 of OAuth flow)${NC}"
if echo "$RECENT_LOGS" | grep -q "Authorization code generated"; then
    echo -e "${GREEN}✓ Authorization code WAS generated${NC}"
    AUTH_CODE=$(echo "$RECENT_LOGS" | grep "Authorization code generated" | tail -1 | sed 's/.*: //' | awk '{print $1}')
    echo "  Code: $AUTH_CODE"
    echo "  Length: ${#AUTH_CODE} characters"
    if [ ${#AUTH_CODE} -ge 16 ]; then
        echo -e "  ${GREEN}✓ Code length is sufficient (≥16 chars)${NC}"
    else
        echo -e "  ${YELLOW}⚠ Code length is short (<16 chars)${NC}"
    fi
    echo ""
else
    echo -e "${RED}✗ Authorization code was NOT generated${NC}"
    echo ""
    echo -e "${YELLOW}ROOT CAUSE: Authorization request validation failed${NC}"
    echo ""
    echo "Checking for error messages..."
    ERROR_MSG=$(echo "$RECENT_LOGS" | grep -A 5 "GET /authorize" | grep -i "error" | tail -1)
    if [ -n "$ERROR_MSG" ]; then
        echo "  Error: $ERROR_MSG"
    fi
    echo ""
    echo "Common causes:"
    echo "  - Invalid client_id parameter"
    echo "  - Invalid redirect_uri parameter"
    echo "  - Missing required parameter (response_type, client_id, redirect_uri)"
    echo ""
    echo "Check Alexa Developer Console configuration:"
    echo "  [ ] Client ID = alexa-music-assistant"
    echo "  [ ] Redirect URI matches Alexa's redirect pattern"
    echo ""
    exit 1
fi

# Diagnostic 3: Was redirect sent to Alexa?
echo -e "${BLUE}3. Redirect to Alexa (Step 3 of OAuth flow)${NC}"
if echo "$RECENT_LOGS" | grep -q "Redirecting to"; then
    echo -e "${GREEN}✓ Redirect WAS sent to Alexa${NC}"
    REDIRECT_URL=$(echo "$RECENT_LOGS" | grep "Redirecting to" | tail -1 | sed 's/.*: //')
    echo "  Redirect URL: $REDIRECT_URL"

    # Validate redirect URL
    if echo "$REDIRECT_URL" | grep -q "pitangui.amazon.com\|layla.amazon.com"; then
        echo -e "  ${GREEN}✓ Redirecting to valid Alexa domain${NC}"
    else
        echo -e "  ${RED}✗ Not redirecting to Alexa domain${NC}"
    fi

    if echo "$REDIRECT_URL" | grep -q "code="; then
        echo -e "  ${GREEN}✓ Authorization code included in redirect${NC}"
    else
        echo -e "  ${RED}✗ Authorization code missing from redirect${NC}"
    fi

    if echo "$REDIRECT_URL" | grep -q "state="; then
        echo -e "  ${GREEN}✓ State parameter included in redirect${NC}"
    else
        echo -e "  ${YELLOW}⚠ State parameter missing (optional but recommended)${NC}"
    fi
    echo ""
else
    echo -e "${RED}✗ Redirect was NOT sent${NC}"
    echo ""
    echo -e "${YELLOW}ROOT CAUSE: Redirect failed after code generation${NC}"
    echo ""
    exit 1
fi

# Diagnostic 4: Was token exchange requested?
echo -e "${BLUE}4. Token Exchange Request (Step 4 of OAuth flow)${NC}"
if echo "$RECENT_LOGS" | grep -q "POST /token"; then
    echo -e "${GREEN}✓ Token exchange request WAS received${NC}"
    echo ""
    echo "Last token request:"
    echo "$RECENT_LOGS" | grep "POST /token" | tail -1 | sed 's/^/  /'
    echo ""
else
    echo -e "${RED}✗ Token exchange request was NOT received${NC}"
    echo ""
    echo -e "${YELLOW}ROOT CAUSE: Alexa didn't complete the redirect or failed before token exchange${NC}"
    echo ""
    echo "Possible reasons:"
    echo "  1. User didn't complete redirect (closed browser)"
    echo "  2. Redirect URL was malformed"
    echo "  3. Alexa rejected the authorization code"
    echo "  4. Network timeout between Alexa and your server"
    echo ""
    echo "Check:"
    echo "  [ ] Alexa app - does it show any error message?"
    echo "  [ ] Try account linking again"
    echo "  [ ] Check if redirect URL was correct (see Step 3 above)"
    echo ""
    exit 1
fi

# Diagnostic 5: Were client credentials validated?
echo -e "${BLUE}5. Client Credentials Validation (Step 5 of OAuth flow)${NC}"
if echo "$RECENT_LOGS" | grep -q "Client credentials validated\|Client authentication"; then
    if echo "$RECENT_LOGS" | grep -q "Client credentials validated"; then
        echo -e "${GREEN}✓ Client credentials WERE validated${NC}"
        CLIENT=$(echo "$RECENT_LOGS" | grep "Client credentials validated" | tail -1 | sed 's/.*: //')
        echo "  Client: $CLIENT"
        echo ""
    else
        echo -e "${RED}✗ Client authentication FAILED${NC}"
        echo ""
        echo -e "${YELLOW}ROOT CAUSE: Client Secret mismatch${NC}"
        echo ""
        echo "Action Items:"
        echo "  [ ] Verify Client Secret in Alexa Developer Console"
        echo "  [ ] Ensure OAuth server has matching client secret"
        echo "  [ ] Check if Basic Auth header is correctly formatted"
        echo ""
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ No client credential validation logs found${NC}"
    echo ""
fi

# Diagnostic 6: Was authorization code validated?
echo -e "${BLUE}6. Authorization Code Validation (Step 6 of OAuth flow)${NC}"
if echo "$RECENT_LOGS" | grep -q "Authorization code validated"; then
    echo -e "${GREEN}✓ Authorization code WAS validated${NC}"
    echo ""
else
    echo -e "${RED}✗ Authorization code validation FAILED${NC}"
    echo ""
    echo "Possible reasons:"
    echo "  - Code expired (>10 minutes since generation)"
    echo "  - Code already used (single use only)"
    echo "  - Code mismatch between authorization and token exchange"
    echo ""
    exit 1
fi

# Diagnostic 7: Were tokens generated?
echo -e "${BLUE}7. Token Generation (Step 7 of OAuth flow)${NC}"
if echo "$RECENT_LOGS" | grep -q "Access token generated"; then
    echo -e "${GREEN}✓ Access token WAS generated${NC}"
    ACCESS_TOKEN=$(echo "$RECENT_LOGS" | grep "Access token generated" | tail -1 | sed 's/.*: //' | awk '{print $1}')
    echo "  Token (first 50 chars): ${ACCESS_TOKEN:0:50}..."
    echo "  Length: ${#ACCESS_TOKEN} characters"
    echo ""
else
    echo -e "${RED}✗ Access token was NOT generated${NC}"
    echo ""
    exit 1
fi

if echo "$RECENT_LOGS" | grep -q "Refresh token generated"; then
    echo -e "${GREEN}✓ Refresh token WAS generated${NC}"
    REFRESH_TOKEN=$(echo "$RECENT_LOGS" | grep "Refresh token generated" | tail -1 | sed 's/.*: //' | awk '{print $1}')
    echo "  Token (first 30 chars): ${REFRESH_TOKEN:0:30}..."
    echo ""
else
    echo -e "${RED}✗ Refresh token was NOT generated${NC}"
    echo ""
fi

# Diagnostic 8: Was token response sent?
echo -e "${BLUE}8. Token Response (Step 8 of OAuth flow)${NC}"
if echo "$RECENT_LOGS" | grep -q "Token response sent successfully"; then
    echo -e "${GREEN}✓ Token response WAS sent to Alexa${NC}"
    echo ""

    # Check HTTP status
    if echo "$RECENT_LOGS" | grep -q "HTTP 200"; then
        echo -e "${GREEN}✓ HTTP 200 OK response${NC}"
    else
        echo -e "${YELLOW}⚠ Check HTTP status code${NC}"
    fi
    echo ""
else
    echo -e "${RED}✗ Token response was NOT sent${NC}"
    echo ""
    exit 1
fi

# Final Summary
echo -e "${CYAN}=== DIAGNOSTIC SUMMARY ===${NC}"
echo ""
echo -e "${GREEN}ALL STEPS COMPLETED SUCCESSFULLY!${NC}"
echo ""
echo "OAuth flow completed all 8 steps:"
echo "  ✓ Authorization request received"
echo "  ✓ Authorization code generated"
echo "  ✓ Redirect sent to Alexa"
echo "  ✓ Token exchange request received"
echo "  ✓ Client credentials validated"
echo "  ✓ Authorization code validated"
echo "  ✓ Tokens generated (access + refresh)"
echo "  ✓ Token response sent"
echo ""
echo -e "${BLUE}Next: Verify account is linked in Alexa app${NC}"
echo ""
echo "Steps:"
echo "  1. Open Alexa app"
echo "  2. Go to: More > Skills & Games > Your Skills"
echo "  3. Find 'Music Assistant' skill"
echo "  4. Should show 'Linked' (not 'Link Account')"
echo ""
echo "If still showing 'Link Account', possible causes:"
echo "  - Alexa didn't store the tokens (Alexa-side issue)"
echo "  - Skill is in development mode (try disabling/re-enabling)"
echo "  - Clear Alexa app cache and try again"
echo ""
