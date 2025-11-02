# Link Music Assistant Account with Alexa Device

**Layer**: 01 - Use Cases
**Actor**: User with Amazon Alexa device and Music Assistant account
**Goal**: Enable voice control of music playback through Alexa devices
**Status**: Implemented - October 26, 2025

## Use Case Summary

A user wants to control music playback in their Music Assistant system using voice commands on their Amazon Alexa device (Echo, Echo Dot, etc.). To do this, they must first link their Music Assistant account with their Alexa device through an account linking process.

## Actors

- **Primary Actor**: End User
  - Has an Amazon account with Alexa device registered
  - Has Music Assistant server with music library
  - Wants voice control capability

- **Secondary Actors**:
  - Amazon Alexa service (mediates authentication)
  - Music Assistant server (provides authentication and music services)

## Preconditions

1. User has active Amazon account with Alexa device
2. Music Assistant server is running and accessible
3. User has Music Assistant credentials or authentication method
4. Alexa skill for Music Assistant is registered in user's Alexa app
5. Music Assistant server is publicly accessible (via proxy/tunnel)

## Main Flow

### Step 1: User Initiates Account Linking
- User opens Alexa mobile app
- User navigates to Skills & Games section
- User finds "Music Assistant" skill
- User taps "Enable To Use" button
- Alexa app opens browser to Music Assistant authorization endpoint

### Step 2: Authentication
- User sees Music Assistant login screen
- User authenticates with Music Assistant credentials (username/password or passkey)
- User is presented with permission consent screen showing requested scopes:
  - `music.read` - Read music library
  - `music.control` - Control playback

### Step 3: Authorization
- User reviews requested permissions
- User taps "Authorize" or "Allow" button
- Music Assistant generates authorization code (valid for 5 minutes)
- Browser redirects back to Alexa with authorization code

### Step 4: Token Exchange
- Alexa backend receives authorization code from redirect
- Alexa service calls Music Assistant `/token` endpoint with:
  - Authorization code
  - Client credentials
  - PKCE verifier (proof key)
- Music Assistant validates code and PKCE, generates tokens:
  - Access token (valid 1 hour)
  - Refresh token (valid 90 days)
  - Returns tokens to Alexa

### Step 5: Completion
- Alexa app displays "Music Assistant has been successfully linked"
- User can now use voice commands to control music

## Postconditions

- Music Assistant account is linked to Alexa device
- Alexa has valid access token for Music Assistant API
- User can speak voice commands to Alexa device
- Voice commands are forwarded to Music Assistant through linked account

## Alternative Flows

### Authentication Failure
- If user enters wrong credentials:
  - Login screen shows error message
  - User can retry authentication
  - Authorization code expires after 5 minutes if not used

### PKCE Validation Failure
- If PKCE verifier doesn't match challenge:
  - Token endpoint returns 400 Bad Request error
  - Alexa app shows "Account linking failed"
  - User must restart account linking process

### Network Failure
- If connection lost during oauth flow:
  - Authorization code becomes invalid
  - User must restart account linking from Alexa app

### Expired Access Token
- After 1 hour, Alexa uses refresh token to get new access token
- If refresh token invalid/expired (90+ days):
  - Alexa can no longer access Music Assistant
  - User must re-link account

## Business Rules

1. **One-time Setup**: Account linking is one-time per user per device
2. **Token Expiration**: Access tokens valid 1 hour, refresh tokens 90 days
3. **Authorization Code**: Single-use code valid only 5 minutes
4. **PKCE Required**: All OAuth requests must use PKCE (Proof Key for Code Exchange)
5. **HTTPS Required**: All endpoints must use HTTPS with valid certificate

## Success Criteria

✅ User successfully linked account
✅ Alexa app shows "successfully linked" confirmation
✅ User receives valid access token and refresh token
✅ User can issue voice commands without re-authentication
✅ Voice commands are successfully forwarded to Music Assistant
✅ Music playback responds to voice control commands

## Non-Functional Requirements

- **Security**: Credentials transmitted only over HTTPS
- **Usability**: Linking process completes in under 2 minutes
- **Reliability**: Account linking succeeds >99% of first attempts
- **Availability**: Authorization service available 24/7

## Related Use Cases

- [PLAY_SONG_BY_VOICE.md](PLAY_SONG_BY_VOICE.md) - User plays song after account linked
- [PAUSE_MUSIC_BY_VOICE.md](PAUSE_MUSIC_BY_VOICE.md) - User pauses playback
- [CONTROL_VOLUME_BY_VOICE.md](CONTROL_VOLUME_BY_VOICE.md) - User adjusts volume

## See Also

- **Interface Contract**: `docs/03_INTERFACES/ALEXA_OAUTH_ENDPOINTS_CONTRACT.md`
- **Implementation**: `docs/04_INFRASTRUCTURE/OAUTH_SERVER_IMPLEMENTATION.md`
- **Procedures**: `docs/05_OPERATIONS/OAUTH_SERVER_STARTUP.md`
