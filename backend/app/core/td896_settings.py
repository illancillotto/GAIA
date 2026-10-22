from pydantic import Field

from app.core.presenze_whatsapp_settings import PresenzeWhatsAppSettings


class Td896Settings(PresenzeWhatsAppSettings):
    """Bollettino TD 896: codice Poste di stampa in proprio; la campionatura stampa un segnaposto."""

    td896_print_authorization: str | None = Field(default=None, alias="TD896_PRINT_AUTHORIZATION")
    td896_sample_mode: bool = Field(default=False, alias="TD896_SAMPLE_MODE")
