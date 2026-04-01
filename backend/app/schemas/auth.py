from pydantic import BaseModel, ConfigDict


class LoginRequest(BaseModel):
    username: str
    password: str


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
    module_anagrafica: bool
    module_utenze: bool
    enabled_modules: list[str]
