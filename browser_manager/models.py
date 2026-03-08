from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

BrowserType = Literal["firefox", "chrome", "brave", "edge"]


@dataclass
class ProxyConfig:
    scheme: str
    host: str
    port: int
    username: str | None = None
    password: str | None = None

    def to_url(self) -> str:
        auth = ""
        if self.username:
            auth = self.username
            if self.password:
                auth += f":{self.password}"
            auth += "@"
        return f"{self.scheme}://{auth}{self.host}:{self.port}"


@dataclass
class BrowserProfile:
    id: str
    name: str
    browser_type: BrowserType
    profile_path: str
    created_at: str
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    group_name: str | None = None
    is_template: bool = False
    start_url: str | None = None
    proxy: str | None = None
    user_agent: str | None = None
    window_size: str | None = None
    extensions: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)


@dataclass
class LaunchRecord:
    profile_id: str
    launched_at: str
    browser_type: str
    pid: int | None
    url: str | None
    success: bool
