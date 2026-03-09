from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from shutil import which

from .models import BrowserProfile


class BrowserAdapter(ABC):
    name: str

    @abstractmethod
    def launch_args(self, profile: BrowserProfile, url: str | None = None) -> list[str]:
        raise NotImplementedError

    @abstractmethod
    def default_candidates(self) -> list[str]:
        raise NotImplementedError

    def validate_binary(self, path: str) -> str:
        p = Path(path).expanduser()
        if p.is_dir():
            exe = p / (f"{self.name}.exe" if sys.platform.startswith("win") else self.name)
            if exe.exists():
                return str(exe)
            raise FileNotFoundError(f"Binary not found in directory: {exe}")
        if p.exists():
            return str(p)
        resolved = which(path)
        if resolved:
            return resolved
        raise FileNotFoundError(f"Cannot find binary: {path}")


class FirefoxAdapter(BrowserAdapter):
    name = "firefox"

    def launch_args(self, profile: BrowserProfile, url: str | None = None) -> list[str]:
        cmd = ["-no-remote", "-profile", profile.profile_path]
        if url:
            cmd.append(url)
        return cmd

    def default_candidates(self) -> list[str]:
        return ["firefox", "firefox.exe"]


class ChromiumAdapter(BrowserAdapter):
    def launch_args(self, profile: BrowserProfile, url: str | None = None) -> list[str]:
        cmd = [f"--user-data-dir={profile.profile_path}", "--new-window"]
        if url:
            cmd.append(url)
        return cmd


class ChromeAdapter(ChromiumAdapter):
    name = "chrome"

    def default_candidates(self) -> list[str]:
        return ["google-chrome", "chrome", "chrome.exe"]


class BraveAdapter(ChromiumAdapter):
    name = "brave"

    def default_candidates(self) -> list[str]:
        return ["brave-browser", "brave", "brave.exe"]


class EdgeAdapter(ChromiumAdapter):
    name = "edge"

    def default_candidates(self) -> list[str]:
        return ["microsoft-edge", "msedge", "msedge.exe"]


class BrowserService:
    def __init__(self):
        self.adapters = {
            "firefox": FirefoxAdapter(),
            "chrome": ChromeAdapter(),
            "brave": BraveAdapter(),
            "edge": EdgeAdapter(),
        }

    def adapter_for(self, browser_type: str) -> BrowserAdapter:
        if browser_type not in self.adapters:
            raise ValueError(f"Unsupported browser type: {browser_type}")
        return self.adapters[browser_type]

    def resolve_binary(self, browser_type: str, configured: str | None = None, env_key: str | None = None) -> str:
        adapter = self.adapter_for(browser_type)
        if configured:
            return adapter.validate_binary(configured)
        if env_key:
            env_val = os.environ.get(env_key)
            if env_val:
                return adapter.validate_binary(env_val)
        for c in adapter.default_candidates():
            r = which(c)
            if r:
                return r
        raise FileNotFoundError(
            f"Binary for {browser_type} not found. Configure it with 'browser set-binary {browser_type} <path>'."
        )
