from __future__ import annotations

import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 3
INVALID_PATH_SEGMENT = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def safe_path_segment(value: str, fallback: str = "sin_usuario") -> str:
    text = INVALID_PATH_SEGMENT.sub("_", (value or "").strip())
    text = re.sub(r"\s+", "_", text).strip(" ._")
    return text or fallback


def scoped_output_dir(root_dir: Path, username: str, period: int, scope: str) -> Path:
    return (
        root_dir
        / safe_path_segment(username.lower())
        / safe_path_segment(str(period), "sin_periodo")
        / safe_path_segment(scope.lower(), "personal")
    )


def database_path(output_dir: Path) -> Path:
    return output_dir / "cargos_sgd.sqlite"


def file_catalog_path(output_dir: Path) -> Path:
    """Catalogo persistente de adjuntos; no se elimina al limpiar registros."""
    return output_dir / "descargas_archivos.sqlite"


def init_file_catalog(output_dir: Path) -> Path:
    path = file_catalog_path(output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS file_downloads (
                relative_path TEXT PRIMARY KEY,
                file_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                master_id INTEGER,
                file_name TEXT NOT NULL,
                mime_type TEXT,
                expected_size INTEGER,
                status TEXT NOT NULL DEFAULT 'pendiente',
                attempts INTEGER NOT NULL DEFAULT 0,
                last_error TEXT,
                downloaded_at TEXT,
                last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_downloads_status ON file_downloads (status)"
        )
        connection.commit()
    return path


def upsert_file_download_tasks(output_dir: Path, tasks: list[dict[str, Any]]) -> None:
    path = init_file_catalog(output_dir)
    if not tasks:
        return
    with closing(sqlite3.connect(path)) as connection:
        connection.executemany(
            """
            INSERT INTO file_downloads (
                relative_path, file_id, document_id, master_id, file_name, mime_type,
                expected_size, status, last_seen_at
            )
            VALUES (
                :relative_path, :file_id, :document_id, :master_id, :file_name, :mime_type,
                :expected_size, 'pendiente', CURRENT_TIMESTAMP
            )
            ON CONFLICT(relative_path) DO UPDATE SET
                file_id = excluded.file_id,
                document_id = excluded.document_id,
                master_id = excluded.master_id,
                file_name = excluded.file_name,
                mime_type = excluded.mime_type,
                expected_size = excluded.expected_size,
                last_seen_at = CURRENT_TIMESTAMP
            """,
            tasks,
        )
        connection.commit()


def mark_file_download(
    output_dir: Path,
    relative_path: str,
    *,
    status: str,
    error: str | None = None,
    attempted: bool = False,
) -> None:
    path = init_file_catalog(output_dir)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(
            """
            UPDATE file_downloads
            SET status = ?,
                attempts = attempts + ?,
                last_error = ?,
                downloaded_at = CASE WHEN ? = 'descargado' THEN CURRENT_TIMESTAMP ELSE downloaded_at END
            WHERE relative_path = ?
            """,
            (status, int(attempted), error, status, relative_path),
        )
        connection.commit()


def file_download_sources(
    db_path: Path,
    *,
    period: int,
    scope: str,
    depe_id: int,
) -> list[tuple[dict[str, Any], int | None, dict[str, Any]]]:
    """Returns (document, master_id, master_document) for every file-bearing source."""
    init_database(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        principal_rows = connection.execute(
            """
            SELECT iddocumento, raw_json
            FROM documents
            WHERE period = ? AND scope = ? AND depe_id = ? AND relation_kind = 'principal'
            """,
            (period, scope, depe_id),
        ).fetchall()
        relation_rows = connection.execute(
            """
            SELECT master_id, related_id, raw_json
            FROM document_relations
            WHERE period = ? AND scope = ? AND depe_id = ?
            """,
            (period, scope, depe_id),
        ).fetchall()

    principals: dict[int, dict[str, Any]] = {}
    for document_id, raw_json in principal_rows:
        try:
            document = json.loads(raw_json)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(document, dict):
            principals[int(document_id)] = document

    sources: list[tuple[dict[str, Any], int | None, dict[str, Any]]] = [
        (document, None, document) for document in principals.values()
    ]
    for master_id, _related_id, raw_json in relation_rows:
        master_document = principals.get(int(master_id))
        if not master_document:
            continue
        try:
            document = json.loads(raw_json)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(document, dict):
            sources.append((document, int(master_id), master_document))
    return sources


def database_has_documents(output_dir: Path) -> bool:
    db_path = database_path(output_dir)
    if not db_path.exists():
        return False
    try:
        with closing(sqlite3.connect(db_path)) as connection:
            value = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    except sqlite3.Error:
        return False
    return int(value or 0) > 0


def user_has_local_data(root_dir: Path, username: str) -> bool:
    if not username.strip():
        return False
    user_dir = root_dir / safe_path_segment(username.lower())
    if not user_dir.exists():
        return False
    return any(database_has_documents(path.parent) for path in user_dir.rglob("cargos_sgd.sqlite"))


def clear_user_databases(root_dir: Path, username: str) -> list[Path]:
    removed: list[Path] = []
    user_dir = root_dir / safe_path_segment(username.lower())
    if not user_dir.exists():
        return removed
    for db_path in user_dir.rglob("cargos_sgd.sqlite"):
        removed.extend(clear_database(db_path.parent))
    return removed


def clear_database(output_dir: Path) -> list[Path]:
    removed: list[Path] = []
    db_path = database_path(output_dir)
    for path in (db_path, db_path.with_name(db_path.name + "-wal"), db_path.with_name(db_path.name + "-shm")):
        if path.exists():
            path.unlink()
            removed.append(path)
    return removed


def read_context(output_dir: Path) -> dict[str, str]:
    db_path = database_path(output_dir)
    if not db_path.exists():
        return {}
    try:
        with closing(sqlite3.connect(db_path)) as connection:
            rows = connection.execute(
                "SELECT key, value FROM metadata WHERE key LIKE 'context.%'"
            ).fetchall()
    except sqlite3.Error:
        return {}
    return {key.removeprefix("context."): value for key, value in rows}


def write_context(output_dir: Path, *, period: int, scope: str, depe_id: int) -> None:
    db_path = database_path(output_dir)
    init_database(db_path)
    values = {
        "context.period": str(period),
        "context.scope": scope,
        "context.depe_id": str(depe_id),
    }
    with closing(sqlite3.connect(db_path)) as connection:
        connection.executemany(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            values.items(),
        )
        connection.commit()


def context_matches(output_dir: Path, *, period: int, scope: str, depe_id: int) -> bool:
    context = read_context(output_dir)
    if not context:
        return not database_path(output_dir).exists()
    return context == {"period": str(period), "scope": scope, "depe_id": str(depe_id)}


def init_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                iddocumento INTEGER PRIMARY KEY,
                period INTEGER NOT NULL,
                scope TEXT NOT NULL,
                depe_id INTEGER NOT NULL,
                relation_kind TEXT NOT NULL DEFAULT 'principal',
                master_id INTEGER,
                document_type TEXT NOT NULL,
                document_number TEXT,
                signer TEXT,
                document_date TEXT,
                subject TEXT,
                addressee TEXT,
                expediente_documento TEXT,
                folios TEXT,
                storage_type TEXT NOT NULL,
                observations TEXT,
                file_count INTEGER NOT NULL DEFAULT 0,
                raw_json TEXT NOT NULL,
                synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_documents_report
            ON documents (period, scope, depe_id, document_type, document_date, document_number)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_documents_principals
            ON documents (period, scope, depe_id, relation_kind, document_type, document_date, document_number)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_documents_related_master
            ON documents (period, scope, depe_id, relation_kind, master_id)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS document_relations (
                period INTEGER NOT NULL,
                scope TEXT NOT NULL,
                depe_id INTEGER NOT NULL,
                master_id INTEGER NOT NULL,
                related_id INTEGER NOT NULL,
                raw_json TEXT NOT NULL,
                synced_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (period, scope, depe_id, master_id, related_id)
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_document_relations_master
            ON document_relations (period, scope, depe_id, master_id)
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_document_relations_related
            ON document_relations (period, scope, depe_id, related_id)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        _migrate_database(connection)
        connection.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        connection.commit()


def _migrate_database(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(documents)").fetchall()}
    if "signer" not in columns:
        connection.execute("ALTER TABLE documents ADD COLUMN signer TEXT")
        columns.add("signer")

    version_row = connection.execute(
        "SELECT value FROM metadata WHERE key = 'schema_version'"
    ).fetchone()
    try:
        current_version = int(version_row[0]) if version_row else 1
    except (TypeError, ValueError):
        current_version = 1

    if current_version < 2:
        rows = connection.execute("SELECT iddocumento, raw_json FROM documents").fetchall()
        updates = []
        for document_id, raw_json in rows:
            try:
                document = json.loads(raw_json)
            except (TypeError, json.JSONDecodeError):
                continue
            updates.append(
                (
                    _signer(document),
                    _expediente_documento(document),
                    document_id,
                )
            )
        if updates:
            connection.executemany(
                "UPDATE documents SET signer = ?, expediente_documento = ? WHERE iddocumento = ?",
                updates,
            )
    if current_version < 3:
        rows = connection.execute(
            """
            SELECT period, scope, depe_id, master_id, iddocumento, raw_json
            FROM documents
            WHERE relation_kind = 'relacionado' AND master_id IS NOT NULL
            """
        ).fetchall()
        if rows:
            connection.executemany(
                """
                INSERT OR REPLACE INTO document_relations (
                    period, scope, depe_id, master_id, related_id, raw_json, synced_at
                )
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                rows,
            )


def upsert_document(
    db_path: Path,
    document: dict[str, Any],
    *,
    period: int,
    scope: str,
    depe_id: int,
    relation_kind: str = "principal",
    master_id: int | None = None,
) -> None:
    init_database(db_path)
    values = normalize_document(
        document,
        period=period,
        scope=scope,
        depe_id=depe_id,
        relation_kind=relation_kind,
        master_id=master_id,
    )
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            INSERT INTO documents (
                iddocumento, period, scope, depe_id, relation_kind, master_id,
                document_type, document_number, signer, document_date, subject, addressee,
                expediente_documento, folios, storage_type, observations, file_count, raw_json, synced_at
            )
            VALUES (
                :iddocumento, :period, :scope, :depe_id, :relation_kind, :master_id,
                :document_type, :document_number, :signer, :document_date, :subject, :addressee,
                :expediente_documento, :folios, :storage_type, :observations, :file_count,
                :raw_json, CURRENT_TIMESTAMP
            )
            ON CONFLICT(iddocumento) DO UPDATE SET
                period = excluded.period,
                scope = excluded.scope,
                depe_id = excluded.depe_id,
                relation_kind = CASE
                    WHEN documents.relation_kind = 'principal' OR excluded.relation_kind = 'principal'
                    THEN 'principal'
                    ELSE excluded.relation_kind
                END,
                master_id = CASE
                    WHEN documents.relation_kind = 'principal' OR excluded.relation_kind = 'principal'
                    THEN NULL
                    ELSE excluded.master_id
                END,
                document_type = excluded.document_type,
                document_number = excluded.document_number,
                signer = excluded.signer,
                document_date = excluded.document_date,
                subject = excluded.subject,
                addressee = excluded.addressee,
                expediente_documento = excluded.expediente_documento,
                folios = excluded.folios,
                storage_type = excluded.storage_type,
                observations = excluded.observations,
                file_count = excluded.file_count,
                raw_json = excluded.raw_json,
                synced_at = CURRENT_TIMESTAMP
            """,
            values,
        )
        connection.commit()


def upsert_documents(
    db_path: Path,
    documents: list[dict[str, Any]],
    *,
    period: int,
    scope: str,
    depe_id: int,
    relation_kind: str = "principal",
    master_id: int | None = None,
) -> int:
    records = [(document, relation_kind, master_id) for document in documents]
    return upsert_document_records(db_path, records, period=period, scope=scope, depe_id=depe_id)


def upsert_document_records(
    db_path: Path,
    records: list[tuple[dict[str, Any], str, int | None]],
    *,
    period: int,
    scope: str,
    depe_id: int,
) -> int:
    if not records:
        return 0

    init_database(db_path)
    values = []
    for document, relation_kind, master_id in records:
        try:
            values.append(
                normalize_document(
                    document,
                    period=period,
                    scope=scope,
                    depe_id=depe_id,
                    relation_kind=relation_kind,
                    master_id=master_id,
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    if not values:
        return 0
    with closing(sqlite3.connect(db_path)) as connection:
        connection.executemany(
            """
            INSERT INTO documents (
                iddocumento, period, scope, depe_id, relation_kind, master_id,
                document_type, document_number, signer, document_date, subject, addressee,
                expediente_documento, folios, storage_type, observations, file_count, raw_json, synced_at
            )
            VALUES (
                :iddocumento, :period, :scope, :depe_id, :relation_kind, :master_id,
                :document_type, :document_number, :signer, :document_date, :subject, :addressee,
                :expediente_documento, :folios, :storage_type, :observations, :file_count,
                :raw_json, CURRENT_TIMESTAMP
            )
            ON CONFLICT(iddocumento) DO UPDATE SET
                period = excluded.period,
                scope = excluded.scope,
                depe_id = excluded.depe_id,
                relation_kind = CASE
                    WHEN documents.relation_kind = 'principal' OR excluded.relation_kind = 'principal'
                    THEN 'principal'
                    ELSE excluded.relation_kind
                END,
                master_id = CASE
                    WHEN documents.relation_kind = 'principal' OR excluded.relation_kind = 'principal'
                    THEN NULL
                    ELSE excluded.master_id
                END,
                document_type = excluded.document_type,
                document_number = excluded.document_number,
                signer = excluded.signer,
                document_date = excluded.document_date,
                subject = excluded.subject,
                addressee = excluded.addressee,
                expediente_documento = excluded.expediente_documento,
                folios = excluded.folios,
                storage_type = excluded.storage_type,
                observations = excluded.observations,
                file_count = excluded.file_count,
                raw_json = excluded.raw_json,
                synced_at = CURRENT_TIMESTAMP
            """,
            values,
        )
        connection.commit()
    return len(values)


def upsert_related_records(
    db_path: Path,
    records: list[tuple[dict[str, Any], int]],
    *,
    period: int,
    scope: str,
    depe_id: int,
) -> int:
    if not records:
        return 0

    document_values: list[dict[str, Any]] = []
    relation_values: list[tuple[int, str, int, int, int, str]] = []
    for document, master_id in records:
        try:
            related_id = _document_id(document)
            document_values.append(
                normalize_document(
                    document,
                    period=period,
                    scope=scope,
                    depe_id=depe_id,
                    relation_kind="relacionado",
                    master_id=None,
                )
            )
            relation_values.append(
                (
                    period,
                    scope,
                    depe_id,
                    int(master_id),
                    related_id,
                    json.dumps(document, ensure_ascii=False, default=str),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue

    if not relation_values:
        return 0

    init_database(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.executemany(
            """
            INSERT INTO documents (
                iddocumento, period, scope, depe_id, relation_kind, master_id,
                document_type, document_number, signer, document_date, subject, addressee,
                expediente_documento, folios, storage_type, observations, file_count, raw_json, synced_at
            )
            VALUES (
                :iddocumento, :period, :scope, :depe_id, :relation_kind, :master_id,
                :document_type, :document_number, :signer, :document_date, :subject, :addressee,
                :expediente_documento, :folios, :storage_type, :observations, :file_count,
                :raw_json, CURRENT_TIMESTAMP
            )
            ON CONFLICT(iddocumento) DO UPDATE SET
                period = excluded.period,
                scope = excluded.scope,
                depe_id = excluded.depe_id,
                relation_kind = CASE
                    WHEN documents.relation_kind = 'principal' OR excluded.relation_kind = 'principal'
                    THEN 'principal'
                    ELSE excluded.relation_kind
                END,
                master_id = CASE
                    WHEN documents.relation_kind = 'principal' OR excluded.relation_kind = 'principal'
                    THEN NULL
                    ELSE excluded.master_id
                END,
                document_type = excluded.document_type,
                document_number = excluded.document_number,
                signer = excluded.signer,
                document_date = excluded.document_date,
                subject = excluded.subject,
                addressee = excluded.addressee,
                expediente_documento = excluded.expediente_documento,
                folios = excluded.folios,
                storage_type = excluded.storage_type,
                observations = excluded.observations,
                file_count = excluded.file_count,
                raw_json = excluded.raw_json,
                synced_at = CURRENT_TIMESTAMP
            """,
            document_values,
        )
        connection.executemany(
            """
            INSERT INTO document_relations (
                period, scope, depe_id, master_id, related_id, raw_json, synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(period, scope, depe_id, master_id, related_id) DO UPDATE SET
                raw_json = excluded.raw_json,
                synced_at = CURRENT_TIMESTAMP
            """,
            relation_values,
        )
        connection.commit()
    return len(relation_values)


def normalize_document(
    document: dict[str, Any],
    *,
    period: int,
    scope: str,
    depe_id: int,
    relation_kind: str,
    master_id: int | None,
) -> dict[str, Any]:
    files = document.get("files") or []
    return {
        "iddocumento": _document_id(document),
        "period": period,
        "scope": scope,
        "depe_id": depe_id,
        "relation_kind": relation_kind,
        "master_id": master_id,
        "document_type": _first_text(document, "tdoc_descripcion", "tipo_documento", default="SIN TIPO"),
        "document_number": _document_number(document),
        "signer": _signer(document),
        "document_date": _first_text(document, "docu_fecha_doc", "fecha_documento", "created_at"),
        "subject": _first_text(document, "docu_asunto", "asunto"),
        "addressee": _addressee(document),
        "expediente_documento": _expediente_documento(document),
        "folios": _first_text(document, "docu_folios", "folios", "docu_numero_folios"),
        "storage_type": "Digital" if files else "Fisico",
        "observations": _first_text(document, "docu_observacion", "observaciones"),
        "file_count": len(files),
        "raw_json": json.dumps(document, ensure_ascii=False, default=str),
    }


def _document_number(document: dict[str, Any]) -> str:
    number = document.get("docu_numero_doc")
    if number is None:
        return str(document.get("iddocumento_text") or _document_id(document, required=False) or "")
    try:
        return str(int(number)).zfill(6)
    except (TypeError, ValueError):
        return str(number)


def _addressee(document: dict[str, Any]) -> str:
    return _first_text(
        document,
        "oper_usudestino",
        "oper_depeid_d",
        "depe_nombre_destino",
        "destinatario",
        "dirigido_a",
    )


def _expediente_documento(document: dict[str, Any]) -> str:
    parts = [
        _first_text(document, "docu_idexma", "expediente", "docu_expediente"),
        str(_document_id(document, required=False) or ""),
    ]
    return " / ".join(part for part in parts if part)


def _signer(document: dict[str, Any]) -> str:
    value = _first_text(
        document,
        "docu_firma",
        "firmante",
        "docu_firmante",
        "docu_firma_nombre",
        "docu_firmado_por",
    )
    if value:
        return value

    for key in ("usuario", "user", "firmador", "signer"):
        nested = document.get(key)
        if isinstance(nested, dict):
            nested_value = _person_name(nested)
            if nested_value:
                return nested_value
    return ""


def _person_name(value: dict[str, Any]) -> str:
    direct = _first_text(value, "name", "nombre", "full_name", "fullname")
    if direct:
        return direct
    parts = [
        _first_text(value, "adm_name", "nombres", "first_name"),
        _first_text(value, "adm_lastname", "apellidos", "last_name"),
    ]
    return " ".join(part for part in parts if part).strip()


def _first_text(document: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = document.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _document_id(document: dict[str, Any], *, required: bool = True) -> int | None:
    for key in ("iddocumento", "document_id", "id_documento", "docu_id", "id"):
        value = document.get(key)
        if value is not None and str(value).strip():
            try:
                return int(value)
            except (TypeError, ValueError):
                break
    if required:
        keys = ", ".join(sorted(document.keys()))
        raise ValueError(f"Documento sin ID usable. Claves recibidas: {keys}")
    return None
