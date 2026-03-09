from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .browser_service import BrowserService
from .models import BrowserProfile
from .storage import Storage


class Launcher:
    def __init__(self, storage: Storage, browser_service: BrowserService):
        self.storage = storage
        self.browser_service = browser_service

    def _apply_firefox_userjs(self, profile: BrowserProfile) -> None:
        if profile.browser_type != "firefox":
            return
        prefs = []
        if profile.start_url:
            prefs.append(f'user_pref("browser.startup.homepage", "{profile.start_url}");')
        if profile.proxy:
            # minimal placeholder: manual proxy mode can be set later with detailed parsing
            prefs.append('user_pref("network.proxy.type", 1);')
        if not prefs:
            return
        user_js = Path(profile.profile_path) / "user.js"
        user_js.write_text("\n".join(prefs) + "\n", encoding="utf-8")

    def launch(self, profile: BrowserProfile, binary_path: str) -> subprocess.Popen:
        self._apply_firefox_userjs(profile)
        adapter = self.browser_service.adapter_for(profile.browser_type)
        url = profile.start_url
        cmd = [binary_path, *adapter.launch_args(profile, url=url)]
        env = None
        if profile.env:
            import os

            env = os.environ.copy()
            env.update(profile.env)

        try:
            proc = subprocess.Popen(cmd, env=env)
            self.storage.add_launch_record(
                {
                    "profile_id": profile.id,
                    "launched_at": datetime.now(timezone.utc).isoformat(),
                    "browser_type": profile.browser_type,
                    "pid": proc.pid,
                    "url": url,
                    "success": True,
                }
            )
            return proc
        except Exception:
            self.storage.add_launch_record(
                {
                    "profile_id": profile.id,
                    "launched_at": datetime.now(timezone.utc).isoformat(),
                    "browser_type": profile.browser_type,
                    "pid": None,
                    "url": url,
                    "success": False,
                }
            )
            raise
