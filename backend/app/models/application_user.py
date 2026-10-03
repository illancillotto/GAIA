from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.modules.network.models import NetworkDevice


class ApplicationUserRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    CED = "ced"
    HR_MANAGER = "hr_manager"
    REVIEWER = "reviewer"
    VIEWER = "viewer"
    OPERATOR = "operator"


class ApplicationUser(Base):
    __tablename__ = "application_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    office_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone_extension: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
    module_gis: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    module_dotazioni: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    module_catasto: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    module_utenze: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    module_operazioni: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    module_riordino: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    module_ruolo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    module_presenze: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    module_organigramma: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_login_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    assigned_network_devices: Mapped[list["NetworkDevice"]] = relationship(
        "NetworkDevice",
        back_populates="assigned_user",
    )

    @property
    def is_super_admin(self) -> bool:
        return self.role == ApplicationUserRole.SUPER_ADMIN.value

    @property
    def enabled_modules(self) -> list[str]:
        if self.is_super_admin:
            return ["accessi", "rete", "inventario", "gis", "catasto", "utenze", "operazioni", "riordino", "ruolo", "presenze", "organigramma", "dotazioni"]

        module_keys = (
            "accessi", "rete", "inventario", "gis", "catasto", "utenze",
            "operazioni", "riordino", "ruolo", "presenze", "organigramma", "dotazioni",
        )
        forbidden = {"accessi", "rete"} if self.role == ApplicationUserRole.CED.value else set()
        return [key for key in module_keys if key not in forbidden and getattr(self, f"module_{key}")]
