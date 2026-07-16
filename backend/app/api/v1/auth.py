"""`/api/v1/auth/*` routes (PLAN §12.2; FR-1). Thin: parse/validate, call one
service method, map to response DTO — no business logic (PLAN §10.1)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.core.rate_limit import rate_limit
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPairResponse,
    UserResponse,
)
from app.services.auth_service import AuthService, TokenPair

router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(rate_limit("auth"))])


def _to_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=str(user.email),
        role=user.role.value,
        identity_status=user.identity_status.value,
    )


def _to_token_response(tokens: TokenPair) -> TokenPairResponse:
    return TokenPairResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in_seconds,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> UserResponse:
    user = AuthService(db).register(email=payload.email, password=payload.password)
    return _to_user_response(user)


@router.post("/login", response_model=TokenPairResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPairResponse:
    _, tokens = AuthService(db).login(email=payload.email, password=payload.password)
    return _to_token_response(tokens)


@router.post("/refresh", response_model=TokenPairResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPairResponse:
    tokens = AuthService(db).refresh(raw_refresh_token=payload.refresh_token)
    return _to_token_response(tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> None:
    AuthService(db).logout(user_id=current_user.id, raw_refresh_token=payload.refresh_token)
