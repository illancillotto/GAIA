"""Reuse GAIA sessions and canonical permissions, never a password grant."""

from fastapi import HTTPException

from app.repositories.application_user import get_application_user_by_id
from app.services.auth import get_current_user_from_token
from app.services.permission_resolver import can_access_section

from .auth import SCOPES, effective_scopes


def gaia_oauth_callbacks(session_factory):
    def user_scopes(subject):
        with session_factory() as database:
            user = get_application_user_by_id(database, int(subject))
            if user is None:
                return set()
            return effective_scopes(database, user, can_access_section) & SCOPES.keys()

    async def authenticate(token):
        with session_factory() as database:
            try:
                user = get_current_user_from_token(database, token)
            except HTTPException:
                return None
            return str(user.id) if user.is_active else None

    return user_scopes, authenticate
