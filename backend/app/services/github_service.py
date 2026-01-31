"""GitHub OAuth service."""

from typing import Dict, Optional
import httpx
from github import Github, GithubException

from app.core.config import get_settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class GitHubOAuthError(Exception):
    """GitHub OAuth related errors."""
    pass


async def get_github_auth_url(state: str) -> str:
    """
    Generate GitHub OAuth authorization URL.
    
    Args:
        state: State parameter (usually user_id) for OAuth flow
        
    Returns:
        GitHub OAuth authorization URL
    """
    settings = get_settings()
    
    auth_url = (
        "https://github.com/login/oauth/authorize"
        f"?client_id={settings.github_client_id}"
        "&scope=read:user public_repo"
        f"&state={state}"
    )
    
    logger.info(f"Generated GitHub auth URL for state: {state}")
    return auth_url


async def exchange_code_for_token(code: str) -> str:
    """
    Exchange OAuth authorization code for access token.
    
    Args:
        code: OAuth authorization code from GitHub
        
    Returns:
        GitHub access token
        
    Raises:
        GitHubOAuthError: If token exchange fails
    """
    settings = get_settings()
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                },
                timeout=10.0
            )
            response.raise_for_status()
            token_data = response.json()
            
            access_token = token_data.get("access_token")
            
            if not access_token:
                error_msg = token_data.get("error_description", "Unknown error")
                logger.error(f"GitHub OAuth token exchange failed: {error_msg}")
                raise GitHubOAuthError(f"Failed to exchange code for token: {error_msg}")
            
            logger.info("Successfully exchanged code for GitHub access token")
            return access_token
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during token exchange: {str(e)}")
            raise GitHubOAuthError(f"HTTP error during token exchange: {str(e)}")


async def verify_github_token(access_token: str) -> Dict[str, any]:
    """
    Verify GitHub access token and get user information.
    
    Args:
        access_token: GitHub access token
        
    Returns:
        Dictionary with user information (login, name, email, etc.)
        
    Raises:
        GitHubOAuthError: If token verification fails
    """
    try:
        github = Github(access_token)
        user = github.get_user()
        
        user_info = {
            "login": user.login,
            "name": user.name,
            "email": user.email,
            "avatar_url": user.avatar_url,
            "html_url": user.html_url,
        }
        
        logger.info(f"Verified GitHub token for user: {user.login}")
        return user_info
        
    except GithubException as e:
        logger.error(f"GitHub API error during token verification: {str(e)}")
        raise GitHubOAuthError(f"Failed to verify GitHub token: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {str(e)}")
        raise GitHubOAuthError(f"Unexpected error: {str(e)}")


async def get_user_repositories(access_token: str) -> list:
    """
    Get user's public repositories (for future use).
    
    Args:
        access_token: GitHub access token
        
    Returns:
        List of repository information
    """
    try:
        github = Github(access_token)
        user = github.get_user()
        repos = user.get_repos()
        
        repo_list = []
        for repo in repos:
            repo_list.append({
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "url": repo.html_url,
                "language": repo.language,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
            })
        
        logger.info(f"Retrieved {len(repo_list)} repositories for user")
        return repo_list
        
    except GithubException as e:
        logger.error(f"GitHub API error retrieving repositories: {str(e)}")
        raise GitHubOAuthError(f"Failed to retrieve repositories: {str(e)}")
