from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthProvidersResponse(BaseModel):
    password: bool = True
    google: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: str
    is_active: bool
    module_accessi: bool
    module_rete: bool
    module_inventario: bool
    module_catasto: bool
    module_utenze: bool
    module_operazioni: bool
    module_riordino: bool
    module_ruolo: bool
    module_inaz: bool
    module_organigramma: bool
    enabled_modules: list[str]


class ApplicationUserInviteResponse(BaseModel):
    user_id: int
    email: str
    expires_at: str
    activation_url: str
    activation_url_path: str
    email_sent: bool


class ApplicationUserActivationInfo(BaseModel):
    user_id: int
    username: str
    email: str
    full_name: str | None
    already_activated: bool


class ApplicationUserActivationRequest(BaseModel):
    password: str


class ApplicationUserActivationResult(BaseModel):
    user_id: int
    username: str
    message: str
