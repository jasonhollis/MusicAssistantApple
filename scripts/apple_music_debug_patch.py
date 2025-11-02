#!/usr/bin/env python3
"""
Debug patch for Apple Music provider authentication.
This adds logging and better error handling to diagnose authentication failures.

To apply: Copy the modified methods to the provider __init__.py file.
"""

# Add this to imports section of __init__.py:
# from music_assistant.helpers.logging import get_logger

# Replace the handle_async_init method (around line 266) with:
async def handle_async_init(self) -> None:
    """Handle async initialization of the provider WITH DEBUGGING."""
    self.logger.info("Starting Apple Music provider initialization...")

    # Get tokens from config
    self._music_user_token = self.config.get_value(CONF_MUSIC_USER_TOKEN)
    self._music_app_token = self.config.get_value(CONF_MUSIC_APP_TOKEN)

    # Log token status (safely, without exposing full tokens)
    if self._music_user_token:
        self.logger.info(
            "Music User Token loaded: %s...%s (length: %d)",
            self._music_user_token[:10] if len(self._music_user_token) > 20 else "SHORT",
            self._music_user_token[-10:] if len(self._music_user_token) > 20 else "TOKEN",
            len(self._music_user_token)
        )
    else:
        self.logger.error("Music User Token is missing!")
        raise LoginFailed("Music User Token is missing. Please authenticate.")

    if self._music_app_token:
        self.logger.info(
            "Music App Token loaded: %s... (length: %d)",
            self._music_app_token[:20] if len(self._music_app_token) > 20 else "SHORT",
            len(self._music_app_token)
        )
    else:
        self.logger.error("Music App Token is missing!")
        raise LoginFailed("Music App Token is missing. Please check configuration.")

    # Validate token format
    import re
    if not re.match(r'^[a-zA-Z0-9=/+]{32,}==$', self._music_user_token):
        self.logger.error("Music User Token has invalid format")
        raise LoginFailed("Music User Token has invalid format")

    # Try to get storefront with better error handling
    try:
        self.logger.info("Fetching user storefront...")
        self._storefront = await self._get_user_storefront()
        self.logger.info("Successfully retrieved storefront: %s", self._storefront)
    except Exception as exc:
        self.logger.error(
            "Failed to retrieve user storefront. This usually indicates "
            "an invalid or expired Music User Token. Error type: %s, Error: %s",
            type(exc).__name__, str(exc)
        )

        # Provide more specific error messages
        if "401" in str(exc) or "Unauthorized" in str(exc):
            raise LoginFailed(
                "Authentication failed (401): Music User Token is invalid or expired. "
                "Please re-authenticate through the Apple Music provider settings."
            )
        elif "403" in str(exc) or "Forbidden" in str(exc):
            raise LoginFailed(
                "Access forbidden (403): Token may not match the app token or "
                "you don't have access to this resource."
            )
        else:
            raise LoginFailed(f"Failed to authenticate with Apple Music: {exc}")

    # Load Widevine CDM files
    try:
        self.logger.info("Loading Widevine CDM files...")
        async with aiofiles.open(
            os.path.join(WIDEVINE_BASE_PATH, DECRYPT_CLIENT_ID_FILENAME), "rb"
        ) as _file:
            self._decrypt_client_id = await _file.read()
        async with aiofiles.open(
            os.path.join(WIDEVINE_BASE_PATH, DECRYPT_PRIVATE_KEY_FILENAME), "rb"
        ) as _file:
            self._decrypt_private_key = await _file.read()
        self.logger.info("Widevine CDM files loaded successfully")
    except FileNotFoundError as e:
        self.logger.warning("Widevine CDM files not found: %s", e)
        # Don't fail here as they might not be needed for all operations
    except Exception as e:
        self.logger.error("Failed to load Widevine CDM files: %s", e)


# Replace the _get_data method (around line 789) with improved error handling:
@throttle_with_retries
async def _get_data(self, endpoint, **kwargs) -> dict[str, Any]:
    """Get data from api WITH BETTER ERROR HANDLING."""
    url = f"https://api.music.apple.com/v1/{endpoint}"
    headers = {"Authorization": f"Bearer {self._music_app_token}"}
    headers["Music-User-Token"] = self._music_user_token

    # Log the request (without exposing full tokens)
    self.logger.debug(
        "API Request: %s, Headers: Auth=Bearer...%s, User-Token=...%s",
        url,
        self._music_app_token[-10:] if self._music_app_token else "None",
        self._music_user_token[-10:] if self._music_user_token else "None"
    )

    async with (
        self.mass.http_session.get(
            url, headers=headers, params=kwargs, ssl=True, timeout=120
        ) as response,
    ):
        # Log response status
        self.logger.debug("API Response: %s - Status: %d", url, response.status)

        if response.status == 404 and "limit" in kwargs and "offset" in kwargs:
            return {}

        # Enhanced error handling with specific messages
        if response.status == 401:
            error_text = await response.text()
            self.logger.error(
                "Authentication failed (401) for %s: %s",
                endpoint,
                error_text[:200] if error_text else "No error details"
            )
            raise LoginFailed(
                "Invalid or expired Music User Token. "
                "Please re-authenticate through the Apple Music provider settings."
            )

        if response.status == 403:
            error_text = await response.text()
            self.logger.error(
                "Access forbidden (403) for %s: %s",
                endpoint,
                error_text[:200] if error_text else "No error details"
            )
            raise LoginFailed(
                "Access forbidden. Token may be expired or incompatible with app token."
            )

        # Existing error handling
        if response.status == 404:
            raise MediaNotFoundError(f"{endpoint} not found")
        if response.status == 504:
            self.logger.debug(
                "Apple Music API Timeout: url=%s, params=%s, response_headers=%s",
                url,
                kwargs,
                response.headers,
            )
            raise ResourceTemporarilyUnavailable("Apple Music API Timeout")
        if response.status == 429:
            self.logger.debug("Apple Music Rate Limiter. Headers: %s", response.headers)
            raise ResourceTemporarilyUnavailable("Apple Music Rate Limiter")
        if response.status == 500:
            raise MusicAssistantError("Unexpected server error when calling Apple Music")

        # For any other error status
        if response.status >= 400:
            error_text = await response.text()
            self.logger.error(
                "API Error %d for %s: %s",
                response.status,
                endpoint,
                error_text[:200] if error_text else "No error details"
            )

        response.raise_for_status()
        return await response.json(loads=json_loads)


# Add a new method for token validation (add after __init__):
async def validate_tokens(self) -> dict:
    """Validate both app and user tokens and return detailed status."""
    results = {
        "app_token_valid": False,
        "user_token_valid": False,
        "storefront": None,
        "errors": []
    }

    # Test app token
    try:
        async with self.mass.http_session.get(
            "https://api.music.apple.com/v1/test",
            headers={"Authorization": f"Bearer {self._music_app_token}"},
            ssl=True,
            timeout=10
        ) as response:
            results["app_token_valid"] = response.status == 200
            if response.status != 200:
                results["errors"].append(f"App token invalid: HTTP {response.status}")
    except Exception as e:
        results["errors"].append(f"App token test failed: {e}")

    # Test user token if app token is valid
    if results["app_token_valid"]:
        try:
            url = "https://api.music.apple.com/v1/me/storefront"
            headers = {
                "Authorization": f"Bearer {self._music_app_token}",
                "Music-User-Token": self._music_user_token
            }
            async with self.mass.http_session.get(
                url, headers=headers, ssl=True, timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    results["user_token_valid"] = True
                    results["storefront"] = data.get("data", [{}])[0].get("id")
                else:
                    results["errors"].append(f"User token invalid: HTTP {response.status}")
                    if response.status == 401:
                        results["errors"].append("Token is expired or invalid")
                    elif response.status == 403:
                        results["errors"].append("Token doesn't match app token")
        except Exception as e:
            results["errors"].append(f"User token test failed: {e}")

    return results