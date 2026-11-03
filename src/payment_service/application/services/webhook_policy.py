from __future__ import annotations

import ipaddress
from dataclasses import dataclass, field
from urllib.parse import urlparse

from payment_service.domain.payment import InvalidWebhookUrlError, WebhookUrl

_LOCAL_HOSTNAMES = frozenset({"localhost"})
_LOCAL_SUFFIXES = (".local", ".internal", ".localhost", ".lan")


@dataclass(frozen=True, slots=True)
class WebhookPolicy:
    strict: bool = False
    allowed_hosts: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def permissive(cls) -> WebhookPolicy:
        return cls(strict=False)

    @classmethod
    def strict_for(cls, allowed_hosts: str = "") -> WebhookPolicy:
        hosts = frozenset(host.strip().lower() for host in allowed_hosts.split(",") if host.strip())
        return cls(strict=True, allowed_hosts=hosts)

    def validate(self, url: WebhookUrl) -> None:
        if not self.strict:
            return
        parsed = urlparse(url.value)
        if parsed.scheme != "https":
            raise InvalidWebhookUrlError("webhook_url must use https")
        if parsed.username is not None or parsed.password is not None:
            raise InvalidWebhookUrlError("webhook_url must not contain credentials")
        host = (parsed.hostname or "").lower()
        if self.allowed_hosts and host not in self.allowed_hosts:
            raise InvalidWebhookUrlError("webhook_url host is not allowed")
        if host in _LOCAL_HOSTNAMES or host.endswith(_LOCAL_SUFFIXES):
            raise InvalidWebhookUrlError("webhook_url must not target local hosts")
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            return
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_multicast
            or address.is_unspecified
        ):
            raise InvalidWebhookUrlError("webhook_url must not target a private address")
