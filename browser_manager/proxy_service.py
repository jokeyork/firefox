from __future__ import annotations

from urllib.parse import urlparse

from .models import ProxyConfig
from .profile_service import ProfileService


class ProxyService:
    def __init__(self, profiles: ProfileService):
        self.profiles = profiles

    def parse_proxy(self, value: str) -> ProxyConfig:
        parsed = urlparse(value)
        if not parsed.scheme or not parsed.hostname or not parsed.port:
            raise ValueError("Invalid proxy URL. Example: socks5://127.0.0.1:9050")
        return ProxyConfig(
            scheme=parsed.scheme,
            host=parsed.hostname,
            port=parsed.port,
            username=parsed.username,
            password=parsed.password,
        )

    def set_proxy(self, profile_name: str, proxy_url: str):
        proxy = self.parse_proxy(proxy_url)
        return self.profiles.update_profile(profile_name, proxy=proxy.to_url())

    def clear_proxy(self, profile_name: str):
        return self.profiles.update_profile(profile_name, proxy=None)
