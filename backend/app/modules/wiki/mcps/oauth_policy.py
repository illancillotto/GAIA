"""Validated retention and absolute session limits for opaque OAuth grants."""

from dataclasses import dataclass, fields


@dataclass(frozen=True)
class OAuthPolicy:
    session_seconds: int = 28800
    cleanup_seconds: int = 60
    max_grants: int = 10000
    max_client_grants: int = 1000

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not int or value < 1:
                raise ValueError("OAuth limits must be positive integers")
        if self.max_client_grants > self.max_grants:
            raise ValueError("Client grant limit must not exceed global limit")

    @classmethod
    def from_environment(cls, environ):
        defaults = cls()
        return cls(
            **{
                field.name: int(
                    environ.get(
                        "GAIA_MCP_OAUTH_" + field.name.upper(), getattr(defaults, field.name)
                    )
                )
                for field in fields(cls)
            }
        )
