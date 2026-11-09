# =============================================================================
# Module: newsagent.store
# Responsibilities: SQLite persistence: items, digests, digest_items, llm_*, runs, trend_reports.
# Dependencies: models
# Dependents: pipeline, web.server, trend, cli
# ADRs: ADR-0009
# Traceability: docs/decisions/README.md
# =============================================================================
"""SQLite persistence."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .models import NormalizedItem

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
  id TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  source_name TEXT,
  source_weight REAL,
  title TEXT,
  summary TEXT,
  url TEXT,
  canonical_url TEXT,
  published_at TEXT,
  date_estimated INTEGER DEFAULT 0,
  first_seen_at TEXT,
  last_seen_at TEXT,
  lang TEXT,
  content_hash TEXT,
  simhash INTEGER,
  section_hint TEXT DEFAULT 'tech',
  expired INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_items_pub ON items(published_at);
CREATE INDEX IF NOT EXISTS idx_items_first_seen ON items(first_seen_at);

CREATE TABLE IF NOT EXISTS digest_items (
  digest_id TEXT,
  item_id TEXT,
  shown_at TEXT,
  PRIMARY KEY (digest_id, item_id)
);

CREATE TABLE IF NOT EXISTS digests (
  id TEXT PRIMARY KEY,
  digest_date TEXT,
  window_days INTEGER,
  item_count INTEGER,
  model TEXT,
  prompt_version TEXT,
  degraded INTEGER,
  markdown_path TEXT,
  tokens_in INTEGER,
  tokens_out INTEGER,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS llm_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  digest_id TEXT,
  model TEXT,
  request_hash TEXT,
  cached INTEGER,
  tokens_in INTEGER,
  tokens_out INTEGER,
  latency_ms INTEGER,
  status TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS llm_cache (
  cache_key TEXT PRIMARY KEY,
  response_json TEXT,
  created_at TEXT
);

CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  started_at TEXT,
  finished_at TEXT,
  stats_json TEXT,
  errors_json TEXT
);

CREATE TABLE IF NOT EXISTS trend_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT,
  window_days INTEGER,
  reports_count INTEGER,
  content TEXT,
  tokens_in INTEGER,
  tokens_out INTEGER,
  latency_ms INTEGER
);
"""


def utc_now() -> datetime:
    """Current timezone-aware UTC datetime.

    Preconditions:
        System clock is available.
    Postconditions:
        datetime aware of UTC.
    Prohibitions:
        Do not use naive datetimes in storage in place of this helper.
    Raises:
        None.
    """
    return datetime.now(timezone.utc)


def to_db(dt: datetime) -> str:
    """Serialize a datetime for SQLite storage.

    Preconditions:
        dt is timezone-aware; naive values are treated as UTC.
    Postconditions:
        UTC ISO-8601 string 'YYYY-MM-DDTHH:MM:SSZ'.
    Prohibitions:
        Do not change the format; range queries depend on it.
    Raises:
        None.
    """
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sql_int64(value: int) -> int:
    """SQLite INTEGER is signed 64-bit; convert unsigned simhash for storage."""
    return value - (1 << 64) if value >= (1 << 63) else value


def from_db(value: str) -> datetime:
    """Parse a SQLite ISO-8601 timestamp.

    Preconditions:
        value was produced by to_db.
    Postconditions:
        Timezone-aware UTC datetime.
    Prohibitions:
        Do not pass arbitrary strings.
    Raises:
        ValueError for invalid input.
    """
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class Store:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")

    def init_schema(self) -> None:
        """Create tables/indexes and add missing columns.

        Preconditions:
            A writable SQLite connection exists.
        Postconditions:
            Nothing; schema is idempotent.
        Prohibitions:
            Do not run destructive migrations here.
        Raises:
            sqlite3.Error on invalid schema/SQL.
        """
        self.conn.executescript(SCHEMA)
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(items)")}
        if "section_hint" not in columns:
            self.conn.execute("ALTER TABLE items ADD COLUMN section_hint TEXT DEFAULT 'tech'")
        self.conn.commit()

    # ---------- items ----------
    def upsert_items(self, items: list[NormalizedItem]) -> int:
        """Insert or update items with last-seen and accurate-date rules.

        Preconditions:
            items are NormalizedItem instances; timestamps are UTC.
        Postconditions:
            Number of attempted writes.
        Prohibitions:
            Do not call for non-normalized data.
        Raises:
            sqlite3.Error on constraint failures.
        """
        sql = """
        INSERT INTO items (
          id, source_id, source_name, source_weight, title, summary, url, canonical_url,
          published_at, date_estimated, first_seen_at, last_seen_at, lang, content_hash, simhash, section_hint, expired
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)
        ON CONFLICT(id) DO UPDATE SET
          last_seen_at = excluded.last_seen_at,
          title = excluded.title,
          summary = excluded.summary,
          source_weight = excluded.source_weight,
          content_hash = excluded.content_hash,
          simhash = excluded.simhash,
          published_at = CASE
              WHEN items.date_estimated = 1 AND excluded.date_estimated = 0 THEN excluded.published_at
              ELSE items.published_at END,
          date_estimated = CASE
              WHEN excluded.date_estimated = 0 THEN 0 ELSE items.date_estimated END
        """
        written = 0
        for item in items:
            self.conn.execute(sql, (
                item.id, item.source_id, item.source_name, item.source_weight,
                item.title, item.summary, item.url, item.canonical_url,
                to_db(item.published_at), int(item.date_estimated),
                to_db(item.first_seen_at), to_db(item.last_seen_at),
                item.lang, item.content_hash, _sql_int64(item.simhash), item.section_hint,
            ))
            written += 1
        self.conn.commit()
        return written

    def get_candidates(self, now: datetime, window_days: int, *, exclude_shown: bool = True) -> list[dict[str, Any]]:
        """Select items within the widest window for ranking.

        Preconditions:
            now is UTC; window_days >= 0; exclude_shown controls full-refresh mode.
        Postconditions:
            Row dicts ordered by publish time desc.
        Prohibitions:
            Do not treat this as the final per-section filter.
        Raises:
            sqlite3.Error on query failures.
        """
        start = to_db(now - timedelta(days=window_days))
        sql = """
            SELECT * FROM items
            WHERE published_at >= ? AND expired = 0
        """
        if exclude_shown:
            sql += " AND id NOT IN (SELECT item_id FROM digest_items)"
        sql += " ORDER BY published_at DESC"
        rows = self.conn.execute(sql, (start,)).fetchall()
        return [dict(row) for row in rows]

    def expire_old(self, now: datetime, max_age_days: int) -> int:
        """Mark items older than the widest window as expired.

        Preconditions:
            now is UTC; max_age_days is >= the per-section windows.
        Postconditions:
            Number of rows updated.
        Prohibitions:
            Do not delete historical rows needed by reports.
        Raises:
            sqlite3.Error on update failures.
        """
        cutoff = to_db(now - timedelta(days=max_age_days))
        cursor = self.conn.execute(
            "UPDATE items SET expired = 1 WHERE expired = 0 AND published_at < ?", (cutoff,)
        )
        self.conn.commit()
        return cursor.rowcount

    def count_items(self) -> int:
        """Count all stored items.

        Preconditions:
            Schema exists.
        Postconditions:
            Integer row count.
        Prohibitions:
            Do not use for windowed counts.
        Raises:
            sqlite3.Error on query failures.
        """
        row = self.conn.execute("SELECT COUNT(*) AS n FROM items").fetchone()
        return int(row["n"])

    # ---------- digests ----------
    def save_digest(
        self,
        *,
        digest_id: str,
        digest_date: str,
        window_days: int,
        item_count: int,
        model: str,
        prompt_version: str,
        degraded: bool,
        markdown_path: str,
        tokens_in: int,
        tokens_out: int,
        item_ids: list[str],
    ) -> None:
        """Record a digest and the shown item ids.

        Preconditions:
            digest_id is unique per run; item_ids exist in items.
        Postconditions:
            Nothing; digest_items rows are inserted OR IGNOREd.
        Prohibitions:
            Do not reuse digest_id across different runs.
        Raises:
            sqlite3.Error on write failures.
        """
        self.conn.execute(
            """
            INSERT OR REPLACE INTO digests
            (id, digest_date, window_days, item_count, model, prompt_version, degraded,
             markdown_path, tokens_in, tokens_out, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (digest_id, digest_date, window_days, item_count, model, prompt_version,
             int(degraded), markdown_path, tokens_in, tokens_out, to_db(utc_now())),
        )
        for item_id in item_ids:
            self.conn.execute(
                "INSERT OR IGNORE INTO digest_items (digest_id, item_id, shown_at) VALUES (?,?,?)",
                (digest_id, item_id, to_db(utc_now())),
            )
        self.conn.commit()

    # ---------- runs ----------
    def save_run(self, run_id: str, started_at: datetime, finished_at: datetime,
                 stats: dict[str, Any], errors: list[str]) -> None:
        """Record a run manifest with stats and errors.

        Preconditions:
            run_id is unique; stats/errors are JSON-serializable.
        Postconditions:
            Nothing.
        Prohibitions:
            Do not store secrets in stats.
        Raises:
            sqlite3.Error on write failures.
        """
        self.conn.execute(
            "INSERT OR REPLACE INTO runs (id, started_at, finished_at, stats_json, errors_json) VALUES (?,?,?,?,?)",
            (run_id, to_db(started_at), to_db(finished_at),
             json.dumps(stats, ensure_ascii=False), json.dumps(errors, ensure_ascii=False)),
        )
        self.conn.commit()

    # ---------- TrendReport ----------
    def save_trend(self, *, created_at: datetime, window_days: int, reports_count: int,
                   content: str, tokens_in: int, tokens_out: int, latency_ms: int) -> None:
        """Persist a trend analysis result.

        Preconditions:
            content is the generated text; metrics are integers.
        Postconditions:
            Nothing.
        Prohibitions:
            Do not store raw historical reports here.
        Raises:
            sqlite3.Error on write failures.
        """
        self.conn.execute(
            """
            INSERT INTO trend_reports
            (created_at, window_days, reports_count, content, tokens_in, tokens_out, latency_ms)
            VALUES (?,?,?,?,?,?,?)
            """,
            (to_db(created_at), window_days, reports_count, content,
             tokens_in, tokens_out, latency_ms),
        )
        self.conn.commit()

    def latest_trend(self) -> dict[str, Any] | None:
        """Return the most recent trend report row.

        Preconditions:
            Schema exists.
        Postconditions:
            Row dict or None.
        Prohibitions:
            Do not assume content is non-empty.
        Raises:
            sqlite3.Error on query failures.
        """
        row = self.conn.execute(
            "SELECT * FROM trend_reports ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None

    # ---------- LLM cache / calls ----------
    def get_llm_cache(self, cache_key: str) -> str | None:
        """Look up a cached LLM response.

        Preconditions:
            cache_key is a stable SHA-256 hash.
        Postconditions:
            Response JSON string or None.
        Prohibitions:
            Do not cache persona-sensitive data across users.
        Raises:
            sqlite3.Error on query failures.
        """
        row = self.conn.execute(
            "SELECT response_json FROM llm_cache WHERE cache_key = ?", (cache_key,)
        ).fetchone()
        return row["response_json"] if row else None

    def put_llm_cache(self, cache_key: str, response_json: str) -> None:
        """Store a cached LLM response.

        Preconditions:
            cache_key is stable; response_json is valid JSON text.
        Postconditions:
            Nothing.
        Prohibitions:
            Do not store secrets or raw API errors.
        Raises:
            sqlite3.Error on write failures.
        """
        self.conn.execute(
            "INSERT OR REPLACE INTO llm_cache (cache_key, response_json, created_at) VALUES (?,?,?)",
            (cache_key, response_json, to_db(utc_now())),
        )
        self.conn.commit()

    def log_llm_call(self, *, digest_id: str, model: str, request_hash: str, cached: bool,
                     tokens_in: int, tokens_out: int, latency_ms: int, status: str) -> None:
        """Record one LLM call for cost/audit.

        Preconditions:
            digest_id exists or is empty; model/status are strings.
        Postconditions:
            Nothing.
        Prohibitions:
            Do not log prompt content or API keys.
        Raises:
            sqlite3.Error on write failures.
        """
        self.conn.execute(
            """
            INSERT INTO llm_calls
            (digest_id, model, request_hash, cached, tokens_in, tokens_out, latency_ms, status, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (digest_id, model, request_hash, int(cached), tokens_in, tokens_out,
             latency_ms, status, to_db(utc_now())),
        )
        self.conn.commit()

    def close(self) -> None:
        """Close the SQLite connection.

        Preconditions:
            Connection is open.
        Postconditions:
            Nothing; further calls fail.
        Prohibitions:
            Do not use the store after closing.
        Raises:
            None.
        """
        self.conn.close()
