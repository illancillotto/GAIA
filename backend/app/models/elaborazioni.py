from app.models.catasto import (
    CatastoBatch as ElaborazioneBatch,
    CatastoBatchKind as ElaborazioneBatchKind,
    CatastoBatchStatus as ElaborazioneBatchStatus,
    CatastoConnectionTest as ElaborazioneConnectionTest,
    CatastoConnectionTestStatus as ElaborazioneConnectionTestStatus,
    CatastoCredential as ElaborazioneCredential,
    CatastoVisuraRequest as ElaborazioneRichiesta,
    CatastoVisuraRequestStatus as ElaborazioneRichiestaStatus,
)

__all__ = [
    "ElaborazioneBatch",
    "ElaborazioneBatchKind",
    "ElaborazioneBatchStatus",
    "ElaborazioneConnectionTest",
    "ElaborazioneConnectionTestStatus",
    "ElaborazioneCredential",
    "ElaborazioneRichiesta",
    "ElaborazioneRichiestaStatus",
]
