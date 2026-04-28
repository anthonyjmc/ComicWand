"""Helpers for outbound network safety checks."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import HTTPException, status

from app.core.config import get_settings


def validate_outbound_asset_url(url: str) -> None:
    """Reject dangerous URLs before worker/service downloads remote assets."""
    parsed_url = urlparse(url)
    scheme = (parsed_url.scheme or "").lower()
    host = (parsed_url.hostname or "").lower()
    if scheme != "https":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only HTTPS asset URLs are allowed")
    if not host:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset URL host is missing")

    settings = get_settings()
    allowed_hosts = settings.parsed_external_asset_allowed_hosts
    if allowed_hosts:
        host_is_allowed = any(host == item or host.endswith(f".{item}") for item in allowed_hosts)
        if not host_is_allowed:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset host is not in allowlist")

    try:
        resolved_addresses = {entry[4][0] for entry in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset host cannot be resolved") from exc

    for address in resolved_addresses:
        parsed_ip = ipaddress.ip_address(address)
        if (
            parsed_ip.is_private
            or parsed_ip.is_loopback
            or parsed_ip.is_link_local
            or parsed_ip.is_multicast
            or parsed_ip.is_reserved
            or parsed_ip.is_unspecified
        ):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset host resolves to disallowed address")
