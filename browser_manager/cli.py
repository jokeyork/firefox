from __future__ import annotations

import argparse
from pathlib import Path

from .browser_service import BrowserService
from .extension_service import ExtensionService
from .launcher import Launcher
from .profile_service import ProfileService
from .proxy_service import ProxyService
from .storage import Storage

APP_DIR = Path.home() / ".local" / "share" / "browser_manager"
PROFILES_DIR = APP_DIR / "profiles"


def build_services():
    storage = Storage(APP_DIR / "data")
    profiles = ProfileService(storage, PROFILES_DIR)
    browsers = BrowserService()
    launcher = Launcher(storage, browsers)
    proxies = ProxyService(profiles)
    exts = ExtensionService(profiles)
    return storage, profiles, browsers, launcher, proxies, exts


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="browser-manager", description="Browser profile manager")
    sub = p.add_subparsers(dest="domain")

    profile = sub.add_parser("profile", help="Manage profiles")
    psub = profile.add_subparsers(dest="action", required=True)

    c = psub.add_parser("create")
    c.add_argument("name")
    c.add_argument("--browser", default="firefox", choices=["firefox", "chrome", "brave", "edge"])
    c.add_argument("--tag", action="append", default=[])
    c.add_argument("--group", default=None)
    c.add_argument("--notes", default="")
    c.add_argument("--start-url", default=None)
    c.add_argument("--from-template", default=None)

    cl = psub.add_parser("clone")
    cl.add_argument("source")
    cl.add_argument("new_name")

    d = psub.add_parser("delete")
    d.add_argument("name")

    l = psub.add_parser("list")
    l.add_argument("--browser", default=None)
    l.add_argument("--tag", default=None)
    l.add_argument("--group", default=None)

    tmpl = psub.add_parser("template")
    tmpl.add_argument("name")
    tmpl.add_argument("--disable", action="store_true")

    browser = sub.add_parser("browser", help="Browser binary settings")
    bsub = browser.add_subparsers(dest="action", required=True)
    sb = bsub.add_parser("set-binary")
    sb.add_argument("browser", choices=["firefox", "chrome", "brave", "edge"])
    sb.add_argument("path")
    gb = bsub.add_parser("show-binary")
    gb.add_argument("browser", choices=["firefox", "chrome", "brave", "edge"])

    launch = sub.add_parser("launch", help="Launch profile")
    launch.add_argument("name")

    proxy = sub.add_parser("proxy", help="Proxy management")
    prsub = proxy.add_subparsers(dest="action", required=True)
    prs = prsub.add_parser("set")
    prs.add_argument("profile")
    prs.add_argument("proxy_url")
    prc = prsub.add_parser("clear")
    prc.add_argument("profile")

    ext = sub.add_parser("ext", help="Extensions")
    exsub = ext.add_subparsers(dest="action", required=True)
    ea = exsub.add_parser("add")
    ea.add_argument("profile")
    ea.add_argument("path")
    el = exsub.add_parser("list")
    el.add_argument("profile")

    logs = sub.add_parser("logs", help="Recent launch history")
    logs.add_argument("--limit", type=int, default=20)

    return p


def main(argv: list[str] | None = None) -> int:
    storage, profiles, browsers, launcher, proxies, exts = build_services()
    args = parser().parse_args(argv)

    try:
        if args.domain == "profile":
            if args.action == "create":
                profile = profiles.create_profile(
                    name=args.name,
                    browser_type=args.browser,
                    tags=args.tag,
                    group_name=args.group,
                    notes=args.notes,
                    start_url=args.start_url,
                    from_template=args.from_template,
                )
                print(f"Created {profile.name} [{profile.browser_type}] at {profile.profile_path}")
            elif args.action == "clone":
                p = profiles.clone_profile(args.source, args.new_name)
                print(f"Cloned to {p.name}")
            elif args.action == "delete":
                p = profiles.delete_profile(args.name)
                print(f"Deleted {p.name}")
            elif args.action == "list":
                rows = profiles.list_profiles(browser_type=args.browser, tag=args.tag, group_name=args.group)
                if not rows:
                    print("No profiles")
                for p in rows:
                    tags = ",".join(p.tags)
                    tmpl = " template" if p.is_template else ""
                    print(f"{p.name}\t{p.browser_type}\tgroup={p.group_name or '-'}\ttags={tags}{tmpl}")
            elif args.action == "template":
                p = profiles.set_template(args.name, enabled=not args.disable)
                print(f"Template flag for {p.name}: {p.is_template}")
            return 0

        if args.domain == "browser":
            key = f"binary_{args.browser}"
            if args.action == "set-binary":
                adapter = browsers.adapter_for(args.browser)
                value = adapter.validate_binary(args.path)
                storage.set_setting(key, value)
                print(f"Saved {args.browser} binary: {value}")
            elif args.action == "show-binary":
                configured = storage.get_setting(key)
                value = browsers.resolve_binary(args.browser, configured=configured)
                print(value)
            return 0

        if args.domain == "launch":
            profile = profiles.get_by_name(args.name)
            if profile is None:
                raise FileNotFoundError(f"Profile not found: {args.name}")
            key = f"binary_{profile.browser_type}"
            configured = storage.get_setting(key)
            binary = browsers.resolve_binary(
                profile.browser_type,
                configured=configured,
                env_key=f"BROWSER_MANAGER_{profile.browser_type.upper()}_BIN",
            )
            proc = launcher.launch(profile, binary)
            print(f"Launched {profile.name} pid={proc.pid}")
            return 0

        if args.domain == "proxy":
            if args.action == "set":
                p = proxies.set_proxy(args.profile, args.proxy_url)
                print(f"Proxy set for {p.name}: {p.proxy}")
            elif args.action == "clear":
                p = proxies.clear_proxy(args.profile)
                print(f"Proxy cleared for {p.name}")
            return 0

        if args.domain == "ext":
            if args.action == "add":
                p = exts.add_extension(args.profile, args.path)
                print(f"Extension added for {p.name}")
            elif args.action == "list":
                for item in exts.list_extensions(args.profile):
                    print(item)
            return 0

        if args.domain == "logs":
            for row in storage.recent_launches(args.limit):
                print(
                    f"{row['launched_at']}\tprofile={row['profile_id']}\tbrowser={row['browser_type']}\tpid={row['pid']}\tsuccess={bool(row['success'])}"
                )
            return 0

        parser().print_help()
        return 0
    except Exception as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
