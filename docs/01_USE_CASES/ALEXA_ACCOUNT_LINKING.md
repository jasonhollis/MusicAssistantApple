# Alexa Skill Account Linking Use Case
**Purpose**: User workflows for linking Alexa skill to Music Assistant account
**Audience**: Users, product managers, UX designers, developers
**Layer**: 01_USE_CASES
**Related**: [00_ARCHITECTURE/OAUTH_PRINCIPLES.md](../00_ARCHITECTURE/OAUTH_PRINCIPLES.md)

## Intent

This document describes how users link their Amazon Alexa voice assistant to their Music Assistant account, enabling voice control of music playback. The workflow follows the OAuth 2.0 authorization code grant pattern, ensuring secure access without sharing passwords.

## Actors

### Primary Actor: Music Assistant User
- Owns a Music Assistant instance
- Uses Amazon Alexa app on mobile device
- Wants to control music via voice commands

### Secondary Actors
- **Amazon Alexa App**: Initiates account linking on behalf of user
- **Music Assistant OAuth Server**: Handles authorization and token issuance
- **Amazon Alexa Service**: Validates linking and stores tokens

## Preconditions

1. User has Music Assistant installed and running
2. User has Amazon Alexa app installed on mobile device
3. Music Assistant has OAuth authorization endpoints accessible via HTTPS
4. User has Music Assistant skill enabled in Alexa app

## Use Case: Link Alexa to Music Assistant

### Main Success Scenario

**Stage 1: User Initiates Linking**

1. User opens Alexa app on mobile device
2. User navigates to "Music Assistant" skill settings
3. User taps "Link Account" or "Enable Skill"
4. Alexa app redirects user to Music Assistant authorization endpoint

**Stage 2: User Grants Authorization**

5. User sees Music Assistant consent screen showing:
   - Service name: "Music Assistant"
   - Requesting party: "Amazon Alexa"
   - Requested permissions:
     - Read music library and playlists
     - Control playback (play, pause, skip)
6. User reviews permissions
7. User taps "Approve & Link Account" button

**Stage 3: Authorization Code Issuance**

8. Music Assistant generates authorization code
9. Music Assistant redirects back to Alexa app with code

**Stage 4: Token Exchange (Automatic)**

10. Alexa app exchanges authorization code for access token
11. Alexa app stores tokens for future use
12. Alexa app displays "Account Successfully Linked" message

**Stage 5: Voice Control Enabled**

13. User can now say: "Alexa, play my Favorites playlist on Music Assistant"
14. Alexa uses stored token to authenticate API request
15. Music Assistant validates token and starts playback

### Postconditions

**Success**:
- User's Alexa account is linked to Music Assistant
- Alexa possesses valid access token (1-hour lifetime)
- Alexa possesses valid refresh token (90-day lifetime)
- User can control Music Assistant via voice commands
- Account linking visible in both Alexa app and Music Assistant

**Failure**:
- No tokens issued
- User sees error message with retry option
- No voice control capabilities granted

## Alternative Flows

### Alternative Flow 1: User Denies Authorization

**Divergence Point**: Step 7 (user reviewing permissions)

**Alternative Steps**:
7a. User taps "Cancel" or closes consent screen
7b. Music Assistant redirects to Alexa with error code
7c. Alexa displays "Account linking cancelled" message
7d. No tokens issued
7e. User can retry linking from skill settings

### Alternative Flow 2: Authorization Code Expires

**Divergence Point**: Step 10 (token exchange)

**Scenario**: User approved authorization but waited >5 minutes before Alexa exchanged the code

**Alternative Steps**:
10a. Alexa attempts token exchange with expired code
10b. Music Assistant validates code and finds it expired
10c. Music Assistant returns error: "Authorization code has expired"
10d. Alexa displays "Account linking failed. Please try again"
10e. User must restart linking process from step 1

### Alternative Flow 3: Network Failure During Authorization

**Divergence Point**: Step 4 (redirect to authorization endpoint)

**Alternative Steps**:
4a. Alexa app attempts to load Music Assistant consent screen
4b. Network timeout or connection refused
4c. Alexa displays "Unable to connect to Music Assistant"
4d. Alexa suggests checking Music Assistant is running and accessible
4e. User can retry when network is available

### Alternative Flow 4: Invalid Redirect URI

**Divergence Point**: Step 1 (Alexa initiating authorization)

**Scenario**: Music Assistant configuration doesn't include Alexa's redirect URI in allowed list

**Alternative Steps**:
1a. Alexa sends authorization request with its redirect URI
1b. Music Assistant validates redirect URI against allowed list
1c. Music Assistant finds redirect URI not pre-registered
1d. Music Assistant returns error screen: "Invalid redirect URI"
1e. Administrator must add Alexa redirect URI to Music Assistant configuration
1f. User retries after configuration update

## Use Case: Refresh Access Token

### Main Success Scenario

**Trigger**: Access token expired (after 1 hour)

1. User says "Alexa, play music on Music Assistant"
2. Alexa detects access token is expired
3. Alexa automatically sends refresh token to Music Assistant
4. Music Assistant validates refresh token
5. Music Assistant issues new access token
6. Alexa retries original request with new token
7. Music playback starts

**User Experience**: Seamless - no user interaction required

### Postconditions

**Success**:
- New access token issued (1-hour lifetime)
- Same refresh token retained (90-day lifetime)
- User experiences no interruption

**Failure**:
- Refresh token invalid or expired
- Alexa prompts user to re-link account
- User must complete linking workflow again

## Use Case: Revoke Alexa Access

### Main Success Scenario

**Trigger**: User wants to remove Alexa's access to Music Assistant

1. User opens Alexa app
2. User navigates to Music Assistant skill settings
3. User taps "Disable Skill" or "Unlink Account"
4. Alexa app sends revocation request to Music Assistant
5. Music Assistant invalidates all tokens for this user/client pair
6. Alexa confirms "Account unlinked"
7. Voice control no longer works until re-linked

### Postconditions

**Success**:
- All access tokens invalidated
- All refresh tokens invalidated
- Alexa can no longer access Music Assistant on user's behalf
- User data on Music Assistant remains intact
- User can re-link at any time

## Workflow Diagrams

### Complete Authorization Flow

```
┌─────────┐                ┌──────────┐               ┌────────────────┐
│  User   │                │  Alexa   │               │ Music Assistant│
│ (Phone) │                │   App    │               │  OAuth Server  │
└────┬────┘                └────┬─────┘               └───────┬────────┘
     │                          │                             │
     │ 1. Tap "Link Account"    │                             │
     ├─────────────────────────>│                             │
     │                          │                             │
     │                          │ 2. GET /authorize?          │
     │                          │    client_id=amazon-alexa   │
     │                          │    redirect_uri=https://... │
     │                          │    state=<random>           │
     │                          │    code_challenge=<SHA256>  │
     │                          ├────────────────────────────>│
     │                          │                             │
     │                          │ 3. Show consent screen      │
     │                          │<────────────────────────────┤
     │                          │                             │
     │ 4. Display consent form  │                             │
     │<─────────────────────────┤                             │
     │                          │                             │
     │ 5. Tap "Approve"         │                             │
     ├─────────────────────────>│                             │
     │                          │                             │
     │                          │ 6. POST /approve            │
     │                          │    (user consent)           │
     │                          ├────────────────────────────>│
     │                          │                             │
     │                          │                             │ 7. Generate
     │                          │                             │    auth code
     │                          │                             │
     │                          │ 8. Redirect with code       │
     │                          │    ?code=<CODE>&state=...   │
     │                          │<────────────────────────────┤
     │                          │                             │
     │                          │ 9. POST /token              │
     │                          │    grant_type=authz_code    │
     │                          │    code=<CODE>              │
     │                          │    code_verifier=<PLAIN>    │
     │                          ├────────────────────────────>│
     │                          │                             │
     │                          │                             │ 10. Validate
     │                          │                             │     PKCE
     │                          │                             │
     │                          │ 11. Return tokens           │
     │                          │     {access_token, ...}     │
     │                          │<────────────────────────────┤
     │                          │                             │
     │ 12. "Successfully Linked"│                             │
     │<─────────────────────────┤                             │
     │                          │                             │
```

### Token Refresh Flow

```
┌──────────┐               ┌────────────────┐
│  Alexa   │               │ Music Assistant│
│  Service │               │  OAuth Server  │
└────┬─────┘               └───────┬────────┘
     │                             │
     │ 1. Access token expired     │
     │    (after 1 hour)           │
     │                             │
     │ 2. POST /token              │
     │    grant_type=refresh_token │
     │    refresh_token=<TOKEN>    │
     ├────────────────────────────>│
     │                             │
     │                             │ 3. Validate
     │                             │    refresh token
     │                             │
     │ 4. New access token         │
     │    {access_token, ...}      │
     │<────────────────────────────┤
     │                             │
     │ 5. Retry API request        │
     │    with new token           │
     │                             │
```

## Business Rules

### BR-1: Authorization Code Lifetime
**Rule**: Authorization codes MUST expire within 5 minutes
**Rationale**: Limits window for code interception attacks
**Enforcement**: OAuth server validates code timestamp on exchange

### BR-2: Single-Use Authorization Codes
**Rule**: Each authorization code can be exchanged for tokens exactly once
**Rationale**: Prevents replay attacks
**Enforcement**: OAuth server invalidates code after first successful exchange
**Exception Handling**: If code used twice, revoke ALL tokens issued for that code

### BR-3: Access Token Lifetime
**Rule**: Access tokens MUST expire within 1 hour
**Rationale**: Limits damage from token theft
**Enforcement**: OAuth server includes expires_in in token response
**User Impact**: Transparent refresh every hour

### BR-4: Refresh Token Lifetime
**Rule**: Refresh tokens MUST expire within 90 days
**Rationale**: Balances security (eventual expiration) with usability (infrequent re-linking)
**Enforcement**: OAuth server validates refresh token timestamp
**User Impact**: User must re-link every 90 days if not using skill

### BR-5: Scope Limitation
**Rule**: Alexa can only request scopes: music.read, music.control, user:read
**Rationale**: Least privilege - Alexa only gets permissions needed for its function
**Enforcement**: OAuth server validates requested scopes against allowed list
**User Impact**: User sees clear list of what Alexa can do

### BR-6: PKCE Required for Public Clients
**Rule**: Mobile and voice assistant clients MUST use PKCE
**Rationale**: Public clients cannot protect client_secret
**Enforcement**: OAuth server configuration marks Alexa as public client
**Implementation**: code_challenge required in authorization, code_verifier required in token exchange

## Exception Scenarios

### Exception 1: User Already Linked Account

**Scenario**: User taps "Link Account" when already linked

**Handling**:
1. Alexa detects existing valid tokens
2. Alexa prompts: "Account already linked. Unlink and re-link?"
3. If user confirms: Revoke existing tokens, start fresh linking
4. If user cancels: Keep existing tokens, return to skill settings

### Exception 2: Multiple Concurrent Linking Attempts

**Scenario**: User taps "Link Account" multiple times rapidly

**Handling**:
1. Each attempt generates separate authorization code
2. Only the first completed flow issues tokens
3. Subsequent attempts with same client_id replace previous tokens
4. User ends up with tokens from most recent successful linking

### Exception 3: Music Assistant Unavailable During Linking

**Scenario**: Music Assistant crashes or restarts during authorization flow

**Handling**:
1. User sees network error or timeout
2. Authorization code (if generated) expires after 5 minutes
3. User must retry linking when Music Assistant is available
4. No tokens issued
5. No partial state stored

### Exception 4: Alexa Account Deleted

**Scenario**: User deletes their Amazon account

**Handling**:
1. Amazon revokes all OAuth tokens for that account
2. Music Assistant receives token revocation webhook (if configured)
3. Music Assistant invalidates stored tokens
4. No action required from user
5. Music Assistant can optionally clean up user metadata

## Success Criteria

### User Perspective
- [ ] User can complete linking in <2 minutes
- [ ] User sees clear description of permissions being granted
- [ ] User can link/unlink account at any time
- [ ] Voice control works immediately after linking
- [ ] No password sharing required

### Technical Perspective
- [ ] Authorization flow completes successfully ≥99.5% of the time
- [ ] Token refresh happens transparently (no user interaction)
- [ ] Authorization codes expire in exactly 5 minutes
- [ ] Access tokens expire in exactly 1 hour
- [ ] PKCE validation prevents code interception

### Security Perspective
- [ ] User password never shared with Alexa
- [ ] User can revoke access without changing password
- [ ] Tokens expire and require renewal
- [ ] CSRF protection via state parameter
- [ ] All communication over HTTPS

## Verification

To verify this use case is properly implemented:

### Manual Testing
1. Open Alexa app on mobile device
2. Navigate to Music Assistant skill
3. Tap "Link Account"
4. Verify consent screen appears with correct permissions
5. Tap "Approve & Link Account"
6. Verify "Successfully Linked" message
7. Say "Alexa, play music on Music Assistant"
8. Verify music starts playing

### Automated Testing
1. Simulate authorization request with valid parameters
2. Verify authorization code generated
3. Simulate token exchange with code_verifier
4. Verify access_token and refresh_token returned
5. Simulate token refresh
6. Verify new access_token issued
7. Simulate expired authorization code
8. Verify error returned

### Security Testing
1. Attempt to use authorization code twice
2. Verify second attempt fails
3. Attempt token exchange without code_verifier (PKCE client)
4. Verify exchange fails
5. Attempt authorization with unregistered redirect_uri
6. Verify error returned
7. Attempt authorization without state parameter
8. Verify warning or error (best practice)

## Related Use Cases

### Complementary: Control Alexa Devices FROM Music Assistant
- **Purpose**: Music Assistant sends playback commands TO Alexa devices
- **Direction**: Opposite of this use case
- **Technology**: alexapy library, not OAuth
- **User Benefit**: Can use both simultaneously

### Related: Re-link After Token Expiration
- **Trigger**: Refresh token expired (90 days of inactivity)
- **User Action**: Same as initial linking
- **System Behavior**: Old tokens invalidated, new tokens issued
- **User Impact**: Must re-approve permissions

### Related: Link Multiple Music Providers
- **Scenario**: User also links Spotify, YouTube Music
- **Integration**: Each provider has separate OAuth flow
- **User Benefit**: Voice control across multiple services
- **Implementation**: Music Assistant routes requests to appropriate provider

## See Also

- **[00_ARCHITECTURE/OAUTH_PRINCIPLES.md](../00_ARCHITECTURE/OAUTH_PRINCIPLES.md)** - OAuth 2.0 architectural principles
- **[02_REFERENCE/OAUTH_CONSTANTS.md](../02_REFERENCE/OAUTH_CONSTANTS.md)** - Token formats and lifetimes
- **[03_INTERFACES/OAUTH_ENDPOINTS.md](../03_INTERFACES/OAUTH_ENDPOINTS.md)** - Endpoint specifications
- **[05_OPERATIONS/ALEXA_TROUBLESHOOTING.md](../05_OPERATIONS/ALEXA_TROUBLESHOOTING.md)** - Common linking issues
