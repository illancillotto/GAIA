from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_active_user
from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse
from app.services.auth import authenticate_user, issue_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, summary="Authenticate application user")
def login(payload: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    user = authenticate_user(db, payload.username, payload.password)
    return TokenResponse(access_token=issue_access_token(user))


@router.get("/me", response_model=CurrentUserResponse, summary="Get current application user")
def me(
    current_user: Annotated[ApplicationUser, Depends(require_active_user)],
) -> CurrentUserResponse:
    return CurrentUserResponse.model_validate(current_user)
