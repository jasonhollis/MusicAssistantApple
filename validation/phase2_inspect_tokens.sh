#!/bin/bash
# Token Inspection Tool
# Extracts and analyzes tokens from OAuth server logs

set -e

echo "=== OAuth Token Inspector ==="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get recent logs
RECENT_LOGS=$(docker logs --tail 200 oauth-server 2>&1)

# Extract tokens
echo -e "${CYAN}1. Extracting tokens from logs...${NC}"
echo ""

# Access Token
if echo "$RECENT_LOGS" | grep -q "Access token generated"; then
    ACCESS_TOKEN=$(echo "$RECENT_LOGS" | grep "Access token generated" | tail -1 | sed 's/.*: //' | awk '{print $1}')
    echo -e "${GREEN}Access Token Found:${NC}"
    echo "  Full token: $ACCESS_TOKEN"
    echo "  Length: ${#ACCESS_TOKEN} characters"
    echo ""

    # Check if JWT
    if [[ $ACCESS_TOKEN == eyJ* ]]; then
        echo -e "  ${BLUE}Format: JWT (JSON Web Token)${NC}"
        echo ""

        # Try to decode JWT (header and payload only)
        echo -e "${CYAN}JWT Header:${NC}"
        HEADER=$(echo "$ACCESS_TOKEN" | cut -d'.' -f1)
        # Add padding if needed
        HEADER_PADDED=$(printf '%s' "$HEADER" | sed 's/-/+/g; s/_/\//g' | awk '{n=length%4; if(n>0){for(i=0;i<4-n;i++){printf "="}}} 1')
        echo "$HEADER_PADDED" | base64 -d 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "  (Could not decode header)"
        echo ""

        echo -e "${CYAN}JWT Payload:${NC}"
        PAYLOAD=$(echo "$ACCESS_TOKEN" | cut -d'.' -f2)
        # Add padding if needed
        PAYLOAD_PADDED=$(printf '%s' "$PAYLOAD" | sed 's/-/+/g; s/_/\//g' | awk '{n=length%4; if(n>0){for(i=0;i<4-n;i++){printf "="}}} 1')
        DECODED_PAYLOAD=$(echo "$PAYLOAD_PADDED" | base64 -d 2>/dev/null || echo "{}")

        if command -v python3 &> /dev/null; then
            echo "$DECODED_PAYLOAD" | python3 -m json.tool 2>/dev/null || echo "$DECODED_PAYLOAD"
        else
            echo "$DECODED_PAYLOAD"
        fi
        echo ""

        # Extract expiration if present
        if echo "$DECODED_PAYLOAD" | grep -q '"exp"'; then
            EXP=$(echo "$DECODED_PAYLOAD" | grep -o '"exp"[^,}]*' | grep -o '[0-9]*')
            if [ -n "$EXP" ]; then
                # Convert Unix timestamp to human-readable (macOS compatible)
                EXP_DATE=$(date -r "$EXP" "+%Y-%m-%d %H:%M:%S %Z" 2>/dev/null || echo "Invalid date")
                echo -e "  ${YELLOW}Expiration (exp):${NC} $EXP_DATE"
                echo ""
            fi
        fi

        # Extract other claims
        if echo "$DECODED_PAYLOAD" | grep -q '"sub"'; then
            SUB=$(echo "$DECODED_PAYLOAD" | grep -o '"sub"[^,}]*' | sed 's/"sub"[: "]*//; s/".*//; s/[, }]*//')
            echo -e "  ${GREEN}Subject (user):${NC} $SUB"
        fi

        if echo "$DECODED_PAYLOAD" | grep -q '"client_id"'; then
            CLIENT=$(echo "$DECODED_PAYLOAD" | grep -o '"client_id"[^,}]*' | sed 's/"client_id"[: "]*//; s/".*//; s/[, }]*//')
            echo -e "  ${GREEN}Client ID:${NC} $CLIENT"
        fi

        if echo "$DECODED_PAYLOAD" | grep -q '"scope"'; then
            SCOPE=$(echo "$DECODED_PAYLOAD" | grep -o '"scope"[^,}]*' | sed 's/"scope"[: "]*//; s/".*//; s/[, }]*//')
            echo -e "  ${GREEN}Scope:${NC} $SCOPE"
        fi
        echo ""

    else
        echo -e "  ${BLUE}Format: Opaque Token (not JWT)${NC}"
        echo ""
    fi

    # Extract expires_in from token response
    if echo "$RECENT_LOGS" | grep -q '"expires_in"'; then
        EXPIRES_IN=$(echo "$RECENT_LOGS" | grep '"expires_in"' | tail -1 | grep -o '"expires_in"[^,}]*' | grep -o '[0-9]*')
        echo -e "  ${YELLOW}Expires In:${NC} $EXPIRES_IN seconds ($((EXPIRES_IN/60)) minutes)"
        echo ""
    fi
else
    echo -e "${RED}✗ No access token found in logs${NC}"
    echo ""
fi

# Refresh Token
if echo "$RECENT_LOGS" | grep -q "Refresh token generated"; then
    REFRESH_TOKEN=$(echo "$RECENT_LOGS" | grep "Refresh token generated" | tail -1 | sed 's/.*: //' | awk '{print $1}')
    echo -e "${GREEN}Refresh Token Found:${NC}"
    echo "  Full token: $REFRESH_TOKEN"
    echo "  Length: ${#REFRESH_TOKEN} characters"
    echo ""

    # Refresh tokens are typically opaque
    echo -e "  ${BLUE}Format: Opaque Token${NC}"
    echo ""
else
    echo -e "${RED}✗ No refresh token found in logs${NC}"
    echo ""
fi

# Authorization Code
if echo "$RECENT_LOGS" | grep -q "Authorization code generated"; then
    AUTH_CODE=$(echo "$RECENT_LOGS" | grep "Authorization code generated" | tail -1 | sed 's/.*: //' | awk '{print $1}')
    echo -e "${GREEN}Authorization Code Found:${NC}"
    echo "  Code: $AUTH_CODE"
    echo "  Length: ${#AUTH_CODE} characters"
    echo ""

    # Check if code was consumed
    if echo "$RECENT_LOGS" | grep -q "Authorization code consumed"; then
        echo -e "  ${YELLOW}Status: Consumed (used for token exchange)${NC}"
    else
        echo -e "  ${GREEN}Status: Active (not yet used)${NC}"
    fi
    echo ""
fi

# Token Response
echo -e "${CYAN}2. Token Response to Alexa:${NC}"
echo ""
if echo "$RECENT_LOGS" | grep -q '"access_token"'; then
    TOKEN_RESPONSE=$(echo "$RECENT_LOGS" | grep -A 10 '"access_token"' | grep -E '^\{.*\}$' | tail -1)
    if [ -n "$TOKEN_RESPONSE" ]; then
        echo "Full response:"
        if command -v python3 &> /dev/null; then
            echo "$TOKEN_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$TOKEN_RESPONSE"
        else
            echo "$TOKEN_RESPONSE"
        fi
    else
        echo "  (Response format not captured in logs)"
    fi
    echo ""
else
    echo -e "${YELLOW}⚠ No token response found in logs${NC}"
    echo ""
fi

# Security Analysis
echo -e "${CYAN}3. Security Analysis:${NC}"
echo ""

SECURITY_ISSUES=0

# Check token length
if [ -n "$ACCESS_TOKEN" ]; then
    if [ ${#ACCESS_TOKEN} -lt 32 ]; then
        echo -e "${RED}✗ Access token is too short (<32 chars) - security risk${NC}"
        SECURITY_ISSUES=$((SECURITY_ISSUES+1))
    else
        echo -e "${GREEN}✓ Access token has sufficient length (≥32 chars)${NC}"
    fi
fi

if [ -n "$REFRESH_TOKEN" ]; then
    if [ ${#REFRESH_TOKEN} -lt 32 ]; then
        echo -e "${RED}✗ Refresh token is too short (<32 chars) - security risk${NC}"
        SECURITY_ISSUES=$((SECURITY_ISSUES+1))
    else
        echo -e "${GREEN}✓ Refresh token has sufficient length (≥32 chars)${NC}"
    fi
fi

# Check token uniqueness
if [ -n "$ACCESS_TOKEN" ] && [ -n "$REFRESH_TOKEN" ]; then
    if [ "$ACCESS_TOKEN" = "$REFRESH_TOKEN" ]; then
        echo -e "${RED}✗ Access token and refresh token are IDENTICAL - critical security flaw${NC}"
        SECURITY_ISSUES=$((SECURITY_ISSUES+1))
    else
        echo -e "${GREEN}✓ Access token and refresh token are different${NC}"
    fi
fi

echo ""

if [ $SECURITY_ISSUES -eq 0 ]; then
    echo -e "${GREEN}✓ No security issues detected${NC}"
else
    echo -e "${RED}✗ Found $SECURITY_ISSUES security issue(s)${NC}"
fi
echo ""

# Usage Examples
echo -e "${CYAN}4. Testing Token Usage:${NC}"
echo ""
echo "To test the access token with Music Assistant API:"
echo ""
if [ -n "$ACCESS_TOKEN" ]; then
    echo "curl -H \"Authorization: Bearer $ACCESS_TOKEN\" \\"
    echo "     http://localhost:8095/api/info"
    echo ""
fi

echo "To test token refresh (when access token expires):"
echo ""
if [ -n "$REFRESH_TOKEN" ]; then
    # Get Funnel URL
    FUNNEL_URL=$(tailscale funnel status 2>/dev/null | grep -o 'https://[^ ]*' | head -1)
    if [ -n "$FUNNEL_URL" ]; then
        echo "curl -X POST \"${FUNNEL_URL}/token\" \\"
        echo "     -H \"Content-Type: application/x-www-form-urlencoded\" \\"
        echo "     -u \"alexa-music-assistant:YOUR_CLIENT_SECRET\" \\"
        echo "     -d \"grant_type=refresh_token\" \\"
        echo "     -d \"refresh_token=$REFRESH_TOKEN\""
        echo ""
    fi
fi

echo -e "${YELLOW}Note: In production, tokens should be stored securely and never logged in plaintext.${NC}"
echo ""
