from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class Storage:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "browser_manager.db"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                browser_type TEXT NOT NULL,
                profile_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                tags TEXT NOT NULL DEFAULT '[]',
                group_name TEXT,
                is_template INTEGER NOT NULL DEFAULT 0,
                start_url TEXT,
                proxy TEXT,
                user_agent TEXT,
                window_size TEXT,
                extensions TEXT NOT NULL DEFAULT '[]',
                env TEXT NOT NULL DEFAULT '{}'
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS launch_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_id TEXT NOT NULL,
                launched_at TEXT NOT NULL,
                browser_type TEXT NOT NULL,
                pid INTEGER,
                url TEXT,
                success INTEGER NOT NULL,
                FOREIGN KEY(profile_id) REFERENCES profiles(id)
            )
            """
        )
        self.conn.commit()

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self.conn.commit()

    def get_setting(self, key: str) -> str | None:
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return None if row is None else row[0]

    def insert_profile(self, data: dict) -> None:
        self.conn.execute(
            """
            INSERT INTO profiles(
                id,name,browser_type,profile_path,created_at,notes,tags,group_name,is_template,
                start_url,proxy,user_agent,window_size,extensions,env
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                data["id"],
                data["name"],
                data["browser_type"],
                data["profile_path"],
                data["created_at"],
                data.get("notes", ""),
                json.dumps(data.get("tags", []), ensure_ascii=False),
                data.get("group_name"),
                1 if data.get("is_template") else 0,
                data.get("start_url"),
                data.get("proxy"),
                data.get("user_agent"),
                data.get("window_size"),
                json.dumps(data.get("extensions", []), ensure_ascii=False),
                json.dumps(data.get("env", {}), ensure_ascii=False),
            ),
        )
        self.conn.commit()

    def update_profile(self, profile_id: str, fields: dict) -> None:
        if not fields:
            return
        normalized = {}
        for k, v in fields.items():
            if k in {"tags", "extensions", "env"}:
                normalized[k] = json.dumps(v, ensure_ascii=False)
            elif k == "is_template":
                normalized[k] = 1 if v else 0
            else:
                normalized[k] = v
        set_clause = ", ".join(f"{k}=?" for k in normalized)
        params = list(normalized.values()) + [profile_id]
        self.conn.execute(f"UPDATE profiles SET {set_clause} WHERE id=?", params)
        self.conn.commit()

    def delete_profile(self, profile_id: str) -> None:
        self.conn.execute("DELETE FROM profiles WHERE id=?", (profile_id,))
        self.conn.commit()

    def get_profile_by_name(self, name: str):
        return self.conn.execute("SELECT * FROM profiles WHERE name=?", (name,)).fetchone()

    def get_profile_by_id(self, profile_id: str):
        return self.conn.execute("SELECT * FROM profiles WHERE id=?", (profile_id,)).fetchone()

    def list_profiles(self, browser_type: str | None = None, tag: str | None = None, group_name: str | None = None):
        rows = self.conn.execute("SELECT * FROM profiles ORDER BY created_at DESC").fetchall()
        result = []
        for row in rows:
            tags = json.loads(row["tags"])
            if browser_type and row["browser_type"] != browser_type:
                continue
            if tag and tag not in tags:
                continue
            if group_name and row["group_name"] != group_name:
                continue
            result.append(row)
        return result

    def add_launch_record(self, rec: dict) -> None:
        self.conn.execute(
            "INSERT INTO launch_records(profile_id, launched_at, browser_type, pid, url, success) VALUES(?,?,?,?,?,?)",
            (
                rec["profile_id"],
                rec["launched_at"],
                rec["browser_type"],
                rec.get("pid"),
                rec.get("url"),
                1 if rec.get("success") else 0,
            ),
        )
        self.conn.commit()

    def recent_launches(self, limit: int = 20):
        return self.conn.execute(
            "SELECT * FROM launch_records ORDER BY launched_at DESC LIMIT ?", (limit,)
        ).fetchall()
