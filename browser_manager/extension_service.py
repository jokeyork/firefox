from __future__ import annotations

from pathlib import Path

from .profile_service import ProfileService


class ExtensionService:
    def __init__(self, profiles: ProfileService):
        self.profiles = profiles

    def add_extension(self, profile_name: str, extension_path: str):
        path = Path(extension_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Extension file not found: {path}")
        profile = self.profiles.get_by_name(profile_name)
        if profile is None:
            raise FileNotFoundError(f"Profile not found: {profile_name}")
        if str(path) not in profile.extensions:
            profile.extensions.append(str(path))
            self.profiles.update_profile(profile_name, extensions=profile.extensions)
        return profile

    def list_extensions(self, profile_name: str) -> list[str]:
        profile = self.profiles.get_by_name(profile_name)
        if profile is None:
            raise FileNotFoundError(f"Profile not found: {profile_name}")
        return profile.extensions
