from app.models.catasto import (
    CatastoBatch as ElaborazioneBatch,
    CatastoBatchStatus as ElaborazioneBatchStatus,
    CatastoConnectionTest as ElaborazioneConnectionTest,
    CatastoConnectionTestStatus as ElaborazioneConnectionTestStatus,
    CatastoCredential as ElaborazioneCredential,
    CatastoVisuraRequest as ElaborazioneRichiesta,
    CatastoVisuraRequestStatus as ElaborazioneRichiestaStatus,
)

__all__ = [
    "ElaborazioneBatch",
    "ElaborazioneBatchStatus",
    "ElaborazioneConnectionTest",
    "ElaborazioneConnectionTestStatus",
    "ElaborazioneCredential",
    "ElaborazioneRichiesta",
    "ElaborazioneRichiestaStatus",
]
