# Play Music by Voice Command

**Layer**: 01 - Use Cases
**Actor**: User with linked Alexa device and Music Assistant
**Goal**: Play a song or album from Music Assistant using voice command
**Status**: Designed - Implementation pending

## Use Case Summary

After linking their Alexa account to Music Assistant, a user can issue voice commands to their Alexa device to play music from their Music Assistant library. The user speaks a voice command to Alexa, which sends the request to Music Assistant's API, and music playback begins.

## Actors

- **Primary Actor**: User with linked Alexa device
- **Secondary Actors**:
  - Amazon Alexa service (processes voice and routes requests)
  - Music Assistant server (processes playback requests)
  - Music providers (Spotify, Apple Music, Tidal, etc.)

## Preconditions

1. User has account linked between Alexa and Music Assistant
2. Alexa has valid access token for Music Assistant
3. Music Assistant has music library loaded with accessible content
4. One or more music providers are configured in Music Assistant
5. Alexa device is online and listening

## Main Flow

### Step 1: User Issues Voice Command
- User speaks: "Alexa, ask Music Assistant to play Bohemian Rhapsody"
- Alexa device captures audio

### Step 2: Alexa Processes Voice
- Alexa service recognizes intent: PlayIntent
- Extracts parameter: song_name = "Bohemian Rhapsody"
- Looks up user's access token for Music Assistant
- Prepares API request

### Step 3: Music Assistant Receives Request
- Music Assistant skill handler receives playback request
- Request includes:
  - User access token (validates account)
  - Song/album/playlist name
  - Optional: artist name, playlist context

### Step 4: Search Music Library
- Music Assistant queries music providers for "Bohemian Rhapsody"
- Searches across all configured providers (Spotify, Apple Music, etc.)
- Returns first matching result with playback URL

### Step 5: Start Playback
- Music Assistant initiates playback on configured player
- Player device (AirPlay speaker, Chromecast, local playback) begins streaming
- Acknowledges to Alexa that playback started

### Step 6: Voice Feedback
- Alexa responds: "Playing Bohemian Rhapsody"
- User hears confirmation and music begins playing

## Postconditions

- Music is playing from Music Assistant's selected player
- User can hear music on their playback device
- User can issue follow-up voice commands (pause, next, etc.)
- Music continues playing until paused or stopped

## Alternative Flows

### Song Not Found
- Music Assistant searches all providers but finds no match
- Music Assistant returns "not found" error
- Alexa responds: "I couldn't find that song"
- Playback does not start

### Multiple Matches Found
- Search returns multiple songs with same name
- Music Assistant returns first match (based on provider order)
- Could be improved with disambiguation (by artist name)

### Playback Device Unavailable
- Music Assistant player is offline or unreachable
- Playback request fails
- Alexa responds: "I couldn't reach your music system"

### Access Token Expired
- User's access token has expired (>1 hour old)
- Alexa uses refresh token to get new access token
- If refresh token also expired (>90 days):
  - Playback fails
  - User must re-link account

### Network Failure
- Connection lost between Alexa and Music Assistant
- Playback request times out
- Alexa responds: "Something went wrong"

## Business Rules

1. **Exact Match Priority**: Search returns exact song matches first
2. **Provider Order**: Search respects configured provider priority
3. **Single Playback**: Only one song plays at a time
4. **User Context**: Request must have valid access token for user's account
5. **Scope Validation**: User account must have `music.control` scope

## Success Criteria

✅ Voice command recognized correctly
✅ Music Assistant receives properly formatted request
✅ Song found in at least one configured provider
✅ Playback starts within 5 seconds of voice command
✅ User hears music on their playback device
✅ Alexa provides voice feedback confirming playback

## Non-Functional Requirements

- **Latency**: Voice command to playback <5 seconds
- **Reliability**: Song plays on first attempt >95% of time
- **Availability**: Music Assistant accessible 99.9% of uptime
- **Scalability**: Support multiple concurrent voice requests

## Edge Cases

- **Song name with special characters**: "Don't Stop Me Now" → handle apostrophes
- **Song name with numbers**: "Mr. 3000" → handle numerals
- **Ambiguous song names**: "Imagine" (John Lennon vs. Ariana Grande) → search correctly
- **Very long song names**: Handle gracefully without truncation
- **Song no longer available**: Provider removed song → return "not found"

## Related Use Cases

- [PAUSE_MUSIC_BY_VOICE.md](PAUSE_MUSIC_BY_VOICE.md) - Pause playback
- [NEXT_SONG_BY_VOICE.md](NEXT_SONG_BY_VOICE.md) - Skip to next song
- [CONTROL_VOLUME_BY_VOICE.md](CONTROL_VOLUME_BY_VOICE.md) - Adjust volume
- [LINK_ALEXA_ACCOUNT.md](LINK_ALEXA_ACCOUNT.md) - Account linking prerequisite

## See Also

- **Architecture**: `docs/00_ARCHITECTURE/WEB_UI_SCALABILITY_PRINCIPLES.md`
- **Implementation**: `docs/04_INFRASTRUCTURE/MUSIC_ASSISTANT_ALEXA_SKILL_LAMBDA.md` (when created)
- **Troubleshooting**: `docs/05_OPERATIONS/ALEXA_AUTH_TROUBLESHOOTING.md`
