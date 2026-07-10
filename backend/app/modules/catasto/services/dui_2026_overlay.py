"""Legacy module alias for the annual DUI overlay service.

New code should import from ``app.modules.catasto.services.dui_overlay``.
This file intentionally exposes the same module object so monkeypatches on
legacy private names keep affecting the real implementation during migration.
"""

from __future__ import annotations

import sys

from app.modules.catasto.services import dui_overlay as _dui_overlay

sys.modules[__name__] = _dui_overlay
