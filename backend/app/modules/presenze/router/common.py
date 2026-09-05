from fastapi import Depends

from app.api.deps import require_module, require_role

RequirePresenzeModule = Depends(require_module("presenze"))
RequirePresenzeAdmin = Depends(require_role("super_admin", "admin"))
