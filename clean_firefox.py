"""Backward-compatible launcher for the new browser_manager CLI.

Examples:
  python clean_firefox.py profile create work --browser firefox
  python clean_firefox.py launch work
  python clean_firefox.py browser set-binary firefox /path/to/firefox
"""

from browser_manager.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
