"""GitHub OAuth callback endpoints."""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User, JerryAuth
from app.services.github_service import exchange_code_for_token, verify_github_token, GitHubOAuthError
from app.utils.encryption import encrypt_token
from app.exceptions import UserNotFoundException, GitHubOAuthException
from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/auth/github", tags=["auth"])


@router.get(
    "/callback",
    summary="GitHub OAuth callback",
    description="GitHub redirects here after user authorization"
)
async def github_callback(
    code: str = Query(..., description="Authorization code from GitHub"),
    state: Optional[str] = Query(None, description="State parameter (user_id)"),
    error: Optional[str] = Query(None, description="Error from GitHub"),
    error_description: Optional[str] = Query(None, description="Error description"),
    db: AsyncSession = Depends(get_db),
):
    """
    GitHub OAuth callback endpoint.
    
    GitHub redirects here after user authorizes (or denies) access.
    Exchanges authorization code for access token and stores it encrypted.
    """
    settings = get_settings()
    
    # Check for OAuth errors
    if error:
        logger.error(f"GitHub OAuth error: {error} - {error_description}")
        return RedirectResponse(
            url=f"{settings.frontend_callback_url}?status=error&message={error_description or error}"
        )
    
    try:
        # Parse user_id from state if provided
        user_id = None
        if state:
            try:
                user_id = uuid.UUID(state)
            except ValueError:
                logger.warning(f"Invalid state parameter: {state}")
                raise GitHubOAuthException("Invalid state parameter")
        
        # Exchange code for access token
        access_token = await exchange_code_for_token(code)
        
        # Verify token and get user info
        github_user_info = await verify_github_token(access_token)
        
        logger.info(f"GitHub user authenticated: {github_user_info['login']}")
        
        # Encrypt access token
        encrypted_token = encrypt_token(access_token)
        
        # If user_id provided via state, link to existing user
        if user_id:
            # Verify user exists
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                raise UserNotFoundException(str(user_id))
            
            # Check if auth record exists
            result = await db.execute(select(JerryAuth).where(JerryAuth.user_id == user_id))
            auth = result.scalar_one_or_none()
            
            if auth:
                # Update existing auth
                auth.github_access_token = encrypted_token
                logger.info(f"Updated GitHub token for user: {user_id}")
            else:
                # Create new auth record
                auth = JerryAuth(
                    user_id=user_id,
                    github_access_token=encrypted_token,
                )
                db.add(auth)
                logger.info(f"Created GitHub auth for user: {user_id}")
            
            await db.commit()
            
            # Redirect to frontend with success
            return RedirectResponse(
                url=f"{settings.frontend_callback_url}?status=success&user_id={user_id}&github_user={github_user_info['login']}"
            )
        else:
            # No state provided - return token info for frontend to handle
            logger.info(f"GitHub OAuth completed without state, returning token info")
            return RedirectResponse(
                url=f"{settings.frontend_callback_url}?status=success&github_user={github_user_info['login']}&github_email={github_user_info.get('email', '')}"
            )
        
    except GitHubOAuthError as e:
        logger.error(f"GitHub OAuth service error: {str(e)}")
        return RedirectResponse(
            url=f"{settings.frontend_callback_url}?status=error&message={str(e)}"
        )
    except GitHubOAuthException as e:
        logger.error(f"GitHub OAuth exception: {e.detail}")
        return RedirectResponse(
            url=f"{settings.frontend_callback_url}?status=error&message={e.detail}"
        )
    except UserNotFoundException as e:
        logger.error(f"User not found: {e.detail}")
        return RedirectResponse(
            url=f"{settings.frontend_callback_url}?status=error&message={e.detail}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in GitHub callback: {str(e)}", exc_info=True)
        return RedirectResponse(
            url=f"{settings.frontend_callback_url}?status=error&message=An unexpected error occurred"
        )
