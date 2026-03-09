from __future__ import annotations

import shutil
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .models import BrowserProfile
from .storage import Storage


class ProfileService:
    def __init__(self, storage: Storage, profiles_root: Path):
        self.storage = storage
        self.profiles_root = profiles_root
        self.profiles_root.mkdir(parents=True, exist_ok=True)

    def _sanitize(self, name: str) -> str:
        cleaned = "".join(ch if ch.isalnum() or ch in "_-" else "-" for ch in name.strip())
        cleaned = cleaned.strip("-")
        if not cleaned:
            raise ValueError("Profile name must contain letters or numbers")
        return cleaned

    def _row_to_profile(self, row) -> BrowserProfile:
        import json

        return BrowserProfile(
            id=row["id"],
            name=row["name"],
            browser_type=row["browser_type"],
            profile_path=row["profile_path"],
            created_at=row["created_at"],
            notes=row["notes"],
            tags=json.loads(row["tags"]),
            group_name=row["group_name"],
            is_template=bool(row["is_template"]),
            start_url=row["start_url"],
            proxy=row["proxy"],
            user_agent=row["user_agent"],
            window_size=row["window_size"],
            extensions=json.loads(row["extensions"]),
            env=json.loads(row["env"]),
        )

    def create_profile(
        self,
        name: str,
        browser_type: str,
        start_url: str | None = None,
        tags: list[str] | None = None,
        group_name: str | None = None,
        notes: str = "",
        from_template: str | None = None,
    ) -> BrowserProfile:
        safe_name = self._sanitize(name)
        now = datetime.now(timezone.utc).isoformat()
        profile_id = str(uuid.uuid4())
        profile_path = self.profiles_root / f"{safe_name}_{profile_id[:8]}"

        template_profile = self.get_by_name(from_template) if from_template else None
        if template_profile:
            shutil.copytree(Path(template_profile.profile_path), profile_path)
        else:
            profile_path.mkdir(parents=True, exist_ok=False)

        profile = BrowserProfile(
            id=profile_id,
            name=safe_name,
            browser_type=browser_type,
            profile_path=str(profile_path),
            created_at=now,
            notes=notes,
            tags=tags or ([] if not template_profile else template_profile.tags.copy()),
            group_name=group_name if group_name is not None else (template_profile.group_name if template_profile else None),
            start_url=start_url if start_url is not None else (template_profile.start_url if template_profile else None),
            proxy=template_profile.proxy if template_profile else None,
            user_agent=template_profile.user_agent if template_profile else None,
            window_size=template_profile.window_size if template_profile else None,
            extensions=[] if not template_profile else template_profile.extensions.copy(),
            env={} if not template_profile else template_profile.env.copy(),
        )
        self.storage.insert_profile(asdict(profile))
        return profile

    def clone_profile(self, source_name: str, new_name: str) -> BrowserProfile:
        source = self.get_by_name(source_name)
        if source is None:
            raise FileNotFoundError(f"Profile not found: {source_name}")
        return self.create_profile(
            name=new_name,
            browser_type=source.browser_type,
            start_url=source.start_url,
            tags=source.tags.copy(),
            group_name=source.group_name,
            notes=source.notes,
            from_template=source.name,
        )

    def get_by_name(self, name: str) -> BrowserProfile | None:
        row = self.storage.get_profile_by_name(name)
        return None if row is None else self._row_to_profile(row)

    def list_profiles(
        self, browser_type: str | None = None, tag: str | None = None, group_name: str | None = None
    ) -> list[BrowserProfile]:
        return [
            self._row_to_profile(r)
            for r in self.storage.list_profiles(browser_type=browser_type, tag=tag, group_name=group_name)
        ]

    def delete_profile(self, name: str) -> BrowserProfile:
        profile = self.get_by_name(name)
        if profile is None:
            raise FileNotFoundError(f"Profile not found: {name}")
        shutil.rmtree(profile.profile_path, ignore_errors=False)
        self.storage.delete_profile(profile.id)
        return profile

    def set_template(self, name: str, enabled: bool = True) -> BrowserProfile:
        profile = self.get_by_name(name)
        if profile is None:
            raise FileNotFoundError(f"Profile not found: {name}")
        self.storage.update_profile(profile.id, {"is_template": enabled})
        profile.is_template = enabled
        return profile

    def update_profile(self, name: str, **fields) -> BrowserProfile:
        profile = self.get_by_name(name)
        if profile is None:
            raise FileNotFoundError(f"Profile not found: {name}")
        self.storage.update_profile(profile.id, fields)
        return self.get_by_name(name)  # type: ignore[return-value]
