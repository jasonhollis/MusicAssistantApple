# Proper Alexa OAuth Integration for Home Assistant OS

## The Problem

The standalone server approach (`start_oauth_server.py` on port 8096) fails because:

1. **Home Assistant OS doesn't manage background processes** - Only services registered with the add-on framework
2. **Process crashes cause 502 errors** - No automatic restart mechanism
3. **Defeats the purpose of HA add-on management** - Bypasses proper service lifecycle

## The Solution

**Integrate OAuth endpoints into Music Assistant's webserver** using `mass.webserver.register_dynamic_route()`

This is the pattern used by other providers (Spotify, Deezer) for authentication flows.

### Architecture Change

```
BEFORE (Broken on HA OS):
Alexa App → Reverse Proxy → Port 8096 (separate unstable process) ✗

AFTER (Proper for HA OS):
Alexa App → Reverse Proxy → Port 8095 (Music Assistant's managed webserver) ✓
                                ↓
                    Music Assistant service
                     (Managed by HA add-on)
```

## Implementation

### Step 1: Modify Alexa Provider

In `/server-2.6.0/music_assistant/providers/alexa/__init__.py`, add to the `loaded_in_mass()` method:

```python
async def loaded_in_mass(self) -> None:
    """Call after the provider has been loaded."""
    # ... existing code ...

    # Register OAuth endpoints for Alexa skill account linking
    # (This makes the Alexa skill able to control Music Assistant)
    try:
        from alexa_oauth_endpoints import register_oauth_routes
        register_oauth_routes(self.mass.webserver.app)
        _LOGGER.info("✅ Alexa OAuth endpoints registered")
    except Exception as e:
        _LOGGER.warning("Failed to register OAuth endpoints: %e", e)
```

### Step 2: Update Reverse Proxy

Change reverse proxy config from:
```
/alexa/* → localhost:8096
```

To:
```
/alexa/* → localhost:8095
```

This routes OAuth requests to Music Assistant's webserver instead of a separate port.

### Step 3: Deploy OAuth Implementation

Keep the `alexa_oauth_endpoints.py` file on the container at `/data/alexa_oauth_endpoints.py` (already deployed).

### Step 4: Remove Standalone Server

No longer needed:
- ~~`/data/start_oauth_server.py`~~ (can be deleted)
- ~~Port 8096~~ (not needed)
- ~~Standalone process management~~ (handled by Music Assistant)

## Why This Works

1. **Proper HA OS Integration**
   - OAuth routes are part of Music Assistant's service
   - Service is managed by Home Assistant add-on framework
   - Automatic restart on failure
   - Proper lifecycle management

2. **Single Port Management**
   - Uses Music Assistant's port 8095
   - One reverse proxy configuration
   - Simplified networking

3. **Service Lifecycle**
   - OAuth endpoints live and die with Music Assistant
   - No separate process to crash
   - Proper logging through Music Assistant's logger

4. **Follows HA OS Patterns**
   - Consistent with how other providers (Spotify, Deezer) handle auth
   - Uses `AuthenticationHelper` and `register_dynamic_route()` patterns
   - Aligns with Music Assistant's architecture

## Testing

Once integrated, test with:

```
1. Trigger account linking in Alexa app
2. Should redirect to: https://dev.jasonhollis.com/alexa/authorize
3. Should show authorization form
4. Should complete token exchange
5. Check Music Assistant logs for OAuth debug output
```

## Code Reference

The `register_oauth_routes()` function already exists in `/data/alexa_oauth_endpoints.py` at line 727-738 and is designed for this exact purpose:

```python
def register_oauth_routes(app: web.Application):
    """
    Register OAuth endpoints with Music Assistant's web server.

    This should be called during provider initialization, similar to
    how Spotify provider registers its callback route.
    """
    app.router.add_get('/alexa/authorize', authorize_endpoint)
    app.router.add_post('/alexa/approve', approve_endpoint)
    app.router.add_post('/alexa/token', token_endpoint)
```

## Next Steps

1. Modify Alexa provider's `loaded_in_mass()` method
2. Update reverse proxy config to route 8095 instead of 8096
3. Remove standalone server files
4. Restart Music Assistant
5. Test account linking flow

This is the correct, Home Assistant OS-compliant way to run OAuth endpoints.
