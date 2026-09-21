"""Persistance KORA — couche SQLite légère (baseline solo-prod).

Modèle : un magasin clé-valeur JSON par « collection » (documents, jobs,
assets, campagnes, chartes…). Chaque module de stockage garde son dict en
mémoire comme **cache write-through** : on écrit en base à chaque `save`,
et on **réhydrate** le cache au démarrage → l'état survit à un redémarrage.

SQLite en mode WAL, une connexion partagée protégée par un verrou : largement
suffisant pour le volume cible (< 20 vidéos/semaine). Postgres plus tard au scale.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

# storage/ à la racine du dépôt (cohérent avec render.service.storage_root)
_DB_PATH = Path(__file__).resolve().parents[2] / "storage" / "kora.db"
_conn: sqlite3.Connection | None = None
_lock = threading.Lock()


def _c() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS kv ("
            " collection TEXT NOT NULL, id TEXT NOT NULL, data TEXT NOT NULL,"
            " created_at REAL NOT NULL, PRIMARY KEY (collection, id))"
        )
        _conn.commit()
    return _conn


def put(collection: str, id: str, data: dict[str, Any]) -> None:
    """Insère ou met à jour. `created_at` n'est posé qu'à la première insertion
    (préserve l'ordre de création pour le tri)."""
    with _lock:
        _c().execute(
            "INSERT INTO kv (collection, id, data, created_at) VALUES (?,?,?,?)"
            " ON CONFLICT(collection, id) DO UPDATE SET data=excluded.data",
            (collection, id, json.dumps(data), time.time()),
        )
        _c().commit()


def get(collection: str, id: str) -> dict[str, Any] | None:
    with _lock:
        row = _c().execute(
            "SELECT data FROM kv WHERE collection=? AND id=?", (collection, id)
        ).fetchone()
    return json.loads(row[0]) if row else None


def all(collection: str) -> list[dict[str, Any]]:
    """Tous les documents d'une collection, plus récents d'abord."""
    with _lock:
        rows = _c().execute(
            "SELECT data FROM kv WHERE collection=? ORDER BY created_at DESC",
            (collection,),
        ).fetchall()
    return [json.loads(r[0]) for r in rows]


def delete(collection: str, id: str) -> bool:
    with _lock:
        cur = _c().execute(
            "DELETE FROM kv WHERE collection=? AND id=?", (collection, id)
        )
        _c().commit()
        return cur.rowcount > 0
