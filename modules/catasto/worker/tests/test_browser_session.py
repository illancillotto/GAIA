from pathlib import Path
import sys


WORKER_ROOT = Path(__file__).resolve().parents[1]

if str(WORKER_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKER_ROOT))

from browser_session import BrowserSession


def test_browser_session_classifies_locked_user_page() -> None:
    message = BrowserSession._classify_login_issue(
        "https://sister3.agenziaentrate.gov.it/Servizi/error_locked.jsp",
        "Utente bloccato",
        "Utente bloccato sul portale SISTER",
    )

    assert message == "Utente SISTER bloccato sul portale Agenzia delle Entrate."


def test_browser_session_classifies_existing_session_page() -> None:
    message = BrowserSession._classify_login_issue(
        "https://sister3.agenziaentrate.gov.it/Servizi/error_locked.jsp",
        "Utente bloccato",
        "Utente gia' in sessione sulla stessa o altra postazione.",
    )

    assert message == "Utente SISTER gia' in sessione su un'altra postazione o browser."


def test_browser_session_classifies_rejected_credentials() -> None:
    message = BrowserSession._classify_login_issue(
        "https://iampe.agenziaentrate.gov.it/sam/UI/Login",
        "Accesso non riuscito",
        "Le credenziali inserite non sono valide.",
    )

    assert message == "Credenziali SISTER rifiutate dal portale Agenzia delle Entrate."
