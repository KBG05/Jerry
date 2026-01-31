"""Custom exceptions for the application."""

from fastapi import HTTPException, status


class UserNotFoundException(HTTPException):
    """Exception raised when user is not found."""

    def __init__(self, user_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found"
        )


class GitHubOAuthException(HTTPException):
    """Exception raised for GitHub OAuth errors."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub OAuth error: {detail}"
        )


class OnboardingIncompleteException(HTTPException):
    """Exception raised when onboarding prerequisites are not met."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Onboarding incomplete: {detail}"
        )


class DuplicateUserException(HTTPException):
    """Exception raised when attempting to create duplicate user."""

    def __init__(self, field: str, value: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with {field} '{value}' already exists"
        )
