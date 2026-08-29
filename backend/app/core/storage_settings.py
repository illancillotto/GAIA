from pydantic import Field
from pydantic_settings import BaseSettings


class StorageSettings(BaseSettings):
    nas_host: str = Field(default="nas.internal.local", alias="NAS_HOST")
    nas_port: int = Field(default=22, alias="NAS_PORT")
    nas_username: str = Field(default="svc_naap", alias="NAS_USERNAME")
    nas_password: str = Field(default="change_me", alias="NAS_PASSWORD")
    nas_private_key_path: str | None = Field(default=None, alias="NAS_PRIVATE_KEY_PATH")
    nas_timeout: int = Field(default=10, alias="NAS_TIMEOUT")
    anagrafica_nas_archive_root: str = Field(
        default="/volume1/settore catasto/ARCHIVIO",
        alias="ANAGRAFICA_NAS_ARCHIVE_ROOT",
    )
    utenze_nas_archive_root: str | None = Field(
        default=None,
        alias="UTENZE_NAS_ARCHIVE_ROOT",
    )
    anagrafica_document_storage_path: str = Field(
        default="/data/anagrafica/documents",
        alias="ANAGRAFICA_DOCUMENT_STORAGE_PATH",
    )
    utenze_document_storage_path: str | None = Field(
        default=None,
        alias="UTENZE_DOCUMENT_STORAGE_PATH",
    )
