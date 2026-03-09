from __future__ import annotations

import html
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .browser_service import BrowserService
from .launcher import Launcher
from .profile_service import ProfileService
from .storage import Storage


def _layout(title: str, body: str, message: str = "") -> str:
    msg_html = f'<div class="msg">{html.escape(message)}</div>' if message else ""
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8" />
<title>{html.escape(title)}</title>
<style>
body {{ font-family: Arial, sans-serif; max-width: 980px; margin: 24px auto; padding: 0 16px; background:#f7f8fa; color:#1f2937; }}
h1 {{ margin-bottom: 8px; }}
.card {{ background:white; border:1px solid #d1d5db; border-radius:10px; padding:16px; margin:14px 0; }}
.row {{ display:flex; gap:8px; align-items:center; flex-wrap:wrap; }}
input, select, button {{ padding:8px 10px; border-radius:8px; border:1px solid #cbd5e1; }}
button {{ background:#2563eb; color:white; border:none; cursor:pointer; }}
button.danger {{ background:#dc2626; }}
table {{ width:100%; border-collapse:collapse; }}
th, td {{ padding:8px; border-bottom:1px solid #e5e7eb; text-align:left; }}
.msg {{ background:#ecfeff; border:1px solid #67e8f9; padding:10px; border-radius:8px; margin:12px 0; }}
.small {{ color:#6b7280; font-size:13px; }}
</style>
</head>
<body>
<h1>Browser Manager</h1>
<div class="small">Управление профилями через localhost</div>
{msg_html}
{body}
</body>
</html>"""


def run_web_ui(
    storage: Storage,
    profiles: ProfileService,
    browsers: BrowserService,
    launcher: Launcher,
    host: str = "127.0.0.1",
    port: int = 8787,
) -> None:
    class Handler(BaseHTTPRequestHandler):
        def _message_from_query(self) -> str:
            query = parse_qs(urlparse(self.path).query)
            return query.get("msg", [""])[0]

        def _redirect(self, msg: str = "") -> None:
            location = "/"
            if msg:
                location += f"?msg={msg.replace(' ', '+')}"
            self.send_response(302)
            self.send_header("Location", location)
            self.end_headers()

        def _read_form(self) -> dict[str, str]:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            data = {k: v[0] for k, v in parse_qs(raw).items()}
            return data

        def do_GET(self):  # noqa: N802
            if urlparse(self.path).path != "/":
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not Found")
                return

            rows = profiles.list_profiles()
            table_rows = ""
            for p in rows:
                table_rows += (
                    "<tr>"
                    f"<td>{html.escape(p.name)}</td>"
                    f"<td>{html.escape(p.browser_type)}</td>"
                    f"<td>{html.escape(p.group_name or '-')}</td>"
                    f"<td>{html.escape(','.join(p.tags) or '-')}</td>"
                    f"<td>{html.escape(p.start_url or '-')}</td>"
                    "<td>"
                    f"<form method='post' action='/open' style='display:inline'><input type='hidden' name='name' value='{html.escape(p.name)}'><button>Открыть</button></form> "
                    f"<form method='post' action='/delete' style='display:inline' onsubmit=\"return confirm('Удалить профиль?');\"><input type='hidden' name='name' value='{html.escape(p.name)}'><button class='danger'>Удалить</button></form>"
                    "</td>"
                    "</tr>"
                )

            body = f"""
<div class="card">
  <h3>Создать новый профиль</h3>
  <form class="row" method="post" action="/create">
    <input name="name" placeholder="Имя профиля" required />
    <select name="browser">
      <option value="firefox">firefox</option>
      <option value="chrome">chrome</option>
      <option value="brave">brave</option>
      <option value="edge">edge</option>
    </select>
    <input name="start_url" placeholder="Стартовый URL (опционально)" />
    <input name="tags" placeholder="Теги через запятую" />
    <input name="group" placeholder="Группа" />
    <button>Создать</button>
  </form>
</div>

<div class="card">
  <h3>Настроить путь до браузера</h3>
  <form class="row" method="post" action="/set-binary">
    <select name="browser">
      <option value="firefox">firefox</option>
      <option value="chrome">chrome</option>
      <option value="brave">brave</option>
      <option value="edge">edge</option>
    </select>
    <input name="path" placeholder="/path/to/browser binary" required />
    <button>Сохранить путь</button>
  </form>
</div>

<div class="card">
  <h3>Профили</h3>
  <table>
    <thead><tr><th>Имя</th><th>Браузер</th><th>Группа</th><th>Теги</th><th>URL</th><th>Действия</th></tr></thead>
    <tbody>{table_rows or '<tr><td colspan="6">Профилей пока нет</td></tr>'}</tbody>
  </table>
</div>
"""

            page = _layout("Browser Manager", body, self._message_from_query())
            data = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):  # noqa: N802
            path = urlparse(self.path).path
            form = self._read_form()
            try:
                if path == "/create":
                    tags = [t.strip() for t in form.get("tags", "").split(",") if t.strip()]
                    profiles.create_profile(
                        name=form.get("name", ""),
                        browser_type=form.get("browser", "firefox"),
                        start_url=form.get("start_url") or None,
                        tags=tags,
                        group_name=form.get("group") or None,
                    )
                    self._redirect("Профиль создан")
                    return
                if path == "/delete":
                    profiles.delete_profile(form.get("name", ""))
                    self._redirect("Профиль удален")
                    return
                if path == "/set-binary":
                    browser = form.get("browser", "firefox")
                    adapter = browsers.adapter_for(browser)
                    normalized = adapter.validate_binary(form.get("path", ""))
                    storage.set_setting(f"binary_{browser}", normalized)
                    self._redirect("Путь к браузеру сохранен")
                    return
                if path == "/open":
                    name = form.get("name", "")
                    profile = profiles.get_by_name(name)
                    if profile is None:
                        raise FileNotFoundError(f"Profile not found: {name}")
                    configured = storage.get_setting(f"binary_{profile.browser_type}")
                    binary = browsers.resolve_binary(profile.browser_type, configured=configured)
                    launcher.launch(profile, binary)
                    self._redirect("Профиль запущен")
                    return
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not Found")
            except Exception as exc:
                self._redirect(f"Ошибка: {exc}")

        def log_message(self, format, *args):  # noqa: A003
            return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Web UI started: http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
