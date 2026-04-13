import os
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


TEST_ENV_DEFAULTS = {
    "APP_ENV": "test",
    "DATABASE_URL": "sqlite:///./.pytest-gaia.db",
    "JWT_SECRET_KEY": "pytest-jwt-secret-key",
    "BOOTSTRAP_ADMIN_PASSWORD": "pytest-bootstrap-admin",
    "CREDENTIAL_MASTER_KEY": "WnCjZ2L63B1kIh_2mDkk8j5M6Bf0dzxN3Qv8QbQwB0A=",
}


for env_name, env_value in TEST_ENV_DEFAULTS.items():
    current = os.environ.get(env_name, "").strip()
    if not current or "change_me" in current:
        os.environ[env_name] = env_value
