#!/usr/bin/env python3
"""
Enhanced OAuth server with comprehensive error logging
Deploy this version to diagnose the 502 error
"""

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
import logging
import sys
import traceback
from typing import Optional

# Enhanced logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/music-assistant-oauth-debug.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Global error handler to catch ALL exceptions
@app.middleware("http")
async def log_requests_and_errors(request: Request, call_next):
    try:
        logger.info(f"=== INCOMING REQUEST ===")
        logger.info(f"Method: {request.method}")
        logger.info(f"URL: {request.url}")
        logger.info(f"Headers: {dict(request.headers)}")

        # Log form data if present
        if request.method == "POST":
            try:
                form_data = await request.form()
                logger.info(f"Form data: {dict(form_data)}")
                # Re-populate form data for the actual handler
                request._form = form_data
            except Exception as e:
                logger.warning(f"Could not parse form data: {e}")

        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"=== UNHANDLED EXCEPTION ===")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception message: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "detail": str(e)}
        )

@app.get("/alexa/authorize")
async def authorize(client_id: str, redirect_uri: str, state: str = None):
    """Authorization endpoint"""
    try:
        logger.info(f"=== AUTHORIZE ENDPOINT ===")
        logger.info(f"client_id: {client_id}")
        logger.info(f"redirect_uri: {redirect_uri}")
        logger.info(f"state: {state}")

        # Generate authorization code
        auth_code = "mock_auth_code_12345"
        redirect_url = f"{redirect_uri}?code={auth_code}"
        if state:
            redirect_url += f"&state={state}"

        logger.info(f"Redirecting to: {redirect_url}")
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logger.error(f"Error in authorize endpoint: {e}")
        logger.error(traceback.format_exc())
        raise

@app.post("/alexa/token")
async def token(
    request: Request,
    grant_type: str = Form(...),
    code: Optional[str] = Form(None),
    client_id: str = Form(...),
    client_secret: Optional[str] = Form(None),
    refresh_token: Optional[str] = Form(None)
):
    """Token endpoint with comprehensive error logging"""
    try:
        logger.info(f"=== TOKEN ENDPOINT START ===")
        logger.info(f"grant_type: {grant_type}")
        logger.info(f"code: {code}")
        logger.info(f"client_id: {client_id}")
        logger.info(f"client_secret: {'<present>' if client_secret else '<missing>'}")
        logger.info(f"refresh_token: {'<present>' if refresh_token else '<missing>'}")

        # Validate grant_type
        if grant_type not in ["authorization_code", "refresh_token"]:
            logger.error(f"Invalid grant_type: {grant_type}")
            raise HTTPException(
                status_code=400,
                detail={"error": "unsupported_grant_type"}
            )

        # Handle authorization_code grant
        if grant_type == "authorization_code":
            logger.info("Processing authorization_code grant")

            if not code:
                logger.error("Missing required parameter: code")
                raise HTTPException(
                    status_code=400,
                    detail={"error": "invalid_request", "error_description": "Missing code"}
                )

            # Validate code (mock validation)
            logger.info(f"Validating authorization code: {code}")

            # Generate tokens
            access_token = "mock_access_token_" + code[:10]
            refresh_token_value = "mock_refresh_token_" + code[:10]

            response = {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "refresh_token": refresh_token_value
            }

            logger.info(f"=== TOKEN ENDPOINT SUCCESS ===")
            logger.info(f"Response: {response}")
            return JSONResponse(content=response)

        # Handle refresh_token grant
        elif grant_type == "refresh_token":
            logger.info("Processing refresh_token grant")

            if not refresh_token:
                logger.error("Missing required parameter: refresh_token")
                raise HTTPException(
                    status_code=400,
                    detail={"error": "invalid_request", "error_description": "Missing refresh_token"}
                )

            # Validate refresh token (mock validation)
            logger.info(f"Validating refresh token: {refresh_token[:20]}...")

            # Generate new access token
            access_token = "mock_access_token_refreshed_" + refresh_token[:10]

            response = {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600
            }

            logger.info(f"=== TOKEN ENDPOINT SUCCESS ===")
            logger.info(f"Response: {response}")
            return JSONResponse(content=response)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"=== UNHANDLED ERROR IN TOKEN ENDPOINT ===")
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception message: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_server_error", "detail": str(e)}
        )

@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        logger.info("Health check requested")
        return {"status": "healthy", "version": "debug"}
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    try:
        import uvicorn
        logger.info("=" * 80)
        logger.info("Starting OAuth Debug Server")
        logger.info("=" * 80)
        logger.info("Registered routes:")
        for route in app.routes:
            logger.info(f"  {route.path} - {route.methods if hasattr(route, 'methods') else 'N/A'}")
        logger.info("=" * 80)

        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8096,
            log_level="debug",
            access_log=True
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
