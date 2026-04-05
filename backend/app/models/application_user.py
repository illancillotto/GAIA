from datetime import datetime
from enum import Enum

try:
    from enum import StrEnum
except ImportError:  # pragma: no cover

    class StrEnum(str, Enum):
        pass


from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ApplicationUserRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class ApplicationUser(Base):
    __tablename__ = "application_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(
        String(32), default=ApplicationUserRole.VIEWER.value, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    module_accessi: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    module_rete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    module_inventario: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    module_catasto: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    module_utenze: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    module_operazioni: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @property
    def is_super_admin(self) -> bool:
        return self.role == ApplicationUserRole.SUPER_ADMIN.value

    @property
    def enabled_modules(self) -> list[str]:
        if self.is_super_admin:
            return ["accessi", "rete", "inventario", "catasto", "utenze", "operazioni"]

        modules: list[str] = []
        if self.module_accessi:
            modules.append("accessi")
        if self.module_rete:
            modules.append("rete")
        if self.module_inventario:
            modules.append("inventario")
        if self.module_catasto:
            modules.append("catasto")
        if self.module_utenze:
            modules.append("utenze")
        if self.module_operazioni:
            modules.append("operazioni")
        return modules
