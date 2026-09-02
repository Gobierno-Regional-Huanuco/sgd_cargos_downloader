from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from cargos_downloader.api import SgdApiClient, SgdApiError
from cargos_downloader.storage import (
    clear_database,
    context_matches,
    database_path,
    file_download_sources,
    init_database,
    mark_file_download,
    upsert_related_records,
    upsert_documents,
    upsert_file_download_tasks,
    write_context,
)


INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')
SPACES = re.compile(r"\s+")


@dataclass
class DownloadOptions:
    service_url: str
    token: str
    output_dir: Path
    scope: str
    depe_id: int
    period: int
    per_page: int
    group_size: int
    include_related: bool
    include_personal_for_office: bool
    related_batch_size: int = 200


@dataclass
class DownloadStats:
    documents: int = 0
    related_documents: int = 0
    records_processed: int = 0
    records_total: int = 0
    related_missing_master_id: int = 0
    related_mismatched_relation: int = 0
    related_with_files_arrays: int = 0
    files_downloaded: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    database_file: Path | None = None


@dataclass
class FileDownloadStats:
    files_total: int = 0
    files_downloaded: int = 0
    files_skipped: int = 0
    files_failed: int = 0
    catalog_file: Path | None = None


def sanitize_filename(value: object, fallback: str = "sin_nombre") -> str:
    text = str(value or "").strip()
    text = INVALID_FILENAME.sub("_", text)
    text = SPACES.sub(" ", text).strip(" ._")
    return text[:160] or fallback


def document_name(document: dict) -> str:
    tipo = sanitize_filename(document.get("tdoc_descripcion"), "DOCUMENTO")
    number = document.get("docu_numero_doc")
    siglas = sanitize_filename(document.get("docu_siglas_doc"), "")
    if number is None:
        number_text = document.get("iddocumento_text") or document.get("iddocumento")
    else:
        number_text = str(number).zfill(6)
    parts = [tipo, str(number_text)]
    if siglas:
        parts.append(siglas)
    return sanitize_filename(" ".join(parts), str(document.get("iddocumento", "documento")))


def range_name(document: dict, group_size: int) -> str:
    value = document.get("docu_numero_doc") or document.get("iddocumento") or 1
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = 1
    group_size = max(1, group_size)
    start = ((max(1, number) - 1) // group_size) * group_size + 1
    end = start + group_size - 1
    return f"{start:06d}-{end:06d}"


def document_folder(base_dir: Path, document: dict, group_size: int) -> Path:
    tipo = sanitize_filename(document.get("tdoc_descripcion"), "DOCUMENTO")
    return base_dir / tipo / range_name(document, group_size) / document_name(document)


def file_name(file_data: dict, prefix: str | None = None) -> str:
    name = sanitize_filename(file_data.get("file_name"), f"archivo_{file_data.get('id')}")
    if "." not in Path(name).name and file_data.get("file_tipo") == "application/pdf":
        name += ".pdf"
    if prefix:
        name = f"{sanitize_filename(prefix)}_{name}"
    return name


def expected_size(file_data: dict) -> int | None:
    raw = file_data.get("file_size")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def should_skip(destination: Path, file_data: dict) -> bool:
    if not destination.exists():
        return False
    size = expected_size(file_data)
    return size is None or destination.stat().st_size == size


def run_download(
    options: DownloadOptions,
    log: Callable[[str], None],
    stopped: Callable[[], bool] | None = None,
    progress: Callable[[int, int, str], None] | None = None,
) -> DownloadStats:
    client = SgdApiClient(options.service_url, token=options.token, timeout=120)
    stats = DownloadStats()
    if not context_matches(
        options.output_dir,
        period=options.period,
        scope=options.scope,
        depe_id=options.depe_id,
    ):
        clear_database(options.output_dir)
        log("Base local limpiada por cambio de contexto.")
    db_path = database_path(options.output_dir)
    init_database(db_path)
    write_context(options.output_dir, period=options.period, scope=options.scope, depe_id=options.depe_id)
    stats.database_file = db_path
    page = 1
    fecha_desde = f"{options.period}-01-01"
    fecha_hasta = f"{options.period}-12-31"
    master_documents: dict[int, dict[str, Any]] = {}

    while True:
        if stopped and stopped():
            log("Descarga cancelada por el usuario.")
            break

        response = client.documents(
            scope=options.scope,
            depe_id=options.depe_id,
            page=page,
            per_page=options.per_page,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            include_files=True,
            include_personal=options.include_personal_for_office,
            with_total=page == 1,
        )
        if page == 1:
            stats.records_total = _response_total(response)
            if progress and stats.records_total:
                progress(stats.records_processed, stats.records_total, "Consultando documentos principales")
        documents = response.get("data", [])
        if not documents:
            break

        if stopped and stopped():
            break

        saved = upsert_documents(
            db_path,
            documents,
            period=options.period,
            scope=options.scope,
            depe_id=options.depe_id,
        )
        stats.documents += saved
        stats.records_processed += len(documents)
        log(f"Pagina {page}: {saved} documentos principales registrados.")
        if progress:
            progress(stats.records_processed, stats.records_total, "Documentos principales")

        for document in documents:
            master_id = int(document["iddocumento"])
            master_documents[master_id] = document

        meta = response.get("meta", {})
        if not meta.get("has_more_pages"):
            break
        page += 1

    if options.include_related and master_documents:
        _sync_related_batches(
            client,
            options,
            db_path,
            list(master_documents),
            log,
            stats,
            stopped,
            progress,
        )

    log(f"Base local actualizada: {db_path}")
    return stats


def _sync_related_batches(
    client: SgdApiClient,
    options: DownloadOptions,
    db_path: Path,
    master_ids: list[int],
    log: Callable[[str], None],
    stats: DownloadStats,
    stopped: Callable[[], bool] | None,
    progress: Callable[[int, int, str], None] | None,
) -> None:
    master_batch_size = max(1, options.related_batch_size)
    related_page_size = max(1, options.per_page)
    for batch_number, document_ids in enumerate(_chunks(master_ids, master_batch_size), start=1):
        if stopped and stopped():
            return

        log(f"Consultando relacionados lote {batch_number}: {len(document_ids)} documentos.")
        page = 1
        batch_total: int | None = None
        batch_total_is_explicit = False
        batch_processed = 0
        while True:
            if stopped and stopped():
                return
            try:
                request_started = perf_counter()
                response = client.related_documents_batch(
                    document_ids,
                    scope=options.scope,
                    depe_id=options.depe_id,
                    include_files=True,
                    page=page,
                    per_page=related_page_size,
                    with_total=page == 1,
                )
                request_seconds = perf_counter() - request_started
            except SgdApiError as exc:
                if exc.status_code == 404:
                    raise SgdApiError(
                        "El backend no expone el endpoint batch de relacionados: "
                        "POST /api/cargos/documentos/relacionados/batch."
                    ) from exc
                raise

            diagnostics = _batch_diagnostics(response)
            parse_started = perf_counter()
            received_records = _iter_batch_related(response)
            parse_seconds = perf_counter() - parse_started
            returned_count = _returned_count(response)
            if page == 1:
                stats.related_missing_master_id += int(diagnostics.get("missing_master_id") or 0)
                stats.related_mismatched_relation += int(diagnostics.get("mismatched_relation") or 0)
                stats.related_with_files_arrays += int(diagnostics.get("has_files_arrays") or 0)
                batch_total, batch_total_is_explicit = _related_total(response)
                if batch_total_is_explicit:
                    stats.records_total += batch_total
                log(
                    "  Diagnostico lote: "
                    f"masters={diagnostics.get('masters_count') or len(document_ids)}, "
                    f"related_total={batch_total if batch_total_is_explicit else 'no informado'}, "
                    f"returned_count={returned_count}, "
                    f"page={diagnostics.get('page', page)}, "
                    f"per_page={diagnostics.get('per_page', related_page_size)}, "
                    f"has_more_pages={_has_more_pages(response)}, "
                    f"missing_master_id={diagnostics.get('missing_master_id', 0)}, "
                    f"mismatched_relation={diagnostics.get('mismatched_relation', 0)}, "
                    f"has_files_arrays={diagnostics.get('has_files_arrays', 0)}."
                )

            related_records: list[tuple[dict[str, Any], int]] = [
                (document, master_id) for master_id, document in received_records
            ]

            save_started = perf_counter()
            saved = upsert_related_records(
                db_path,
                related_records,
                period=options.period,
                scope=options.scope,
                depe_id=options.depe_id,
            )
            save_seconds = perf_counter() - save_started
            stats.related_documents += saved
            page_processed = max(returned_count, len(related_records), saved)
            stats.records_processed += page_processed
            batch_processed += page_processed
            if not batch_total_is_explicit:
                stats.records_total += page_processed
            log(
                f"  Lote {batch_number} pagina {page}: "
                f"recibidos={len(related_records)}, guardados={saved}, "
                f"avance={batch_processed}/{batch_total if batch_total_is_explicit else batch_processed}, "
                f"tiempos api={request_seconds:.1f}s parse={parse_seconds:.1f}s sqlite={save_seconds:.1f}s."
            )
            if not related_records:
                log(f"  Lote {batch_number} pagina {page}: sin registros parseables. Claves: {_response_keys(response)}.")
            if progress:
                progress(stats.records_processed, stats.records_total, "Documentos relacionados")

            if not _has_more_pages(response) or not related_records:
                break
            page += 1


def _response_total(response: dict[str, Any]) -> int:
    meta = response.get("meta")
    candidates = []
    if isinstance(meta, dict):
        candidates.extend([meta.get("total"), meta.get("total_count")])
    candidates.extend([response.get("total"), response.get("total_count")])
    for value in candidates:
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            pass
    return 0


def _related_total(response: dict[str, Any]) -> tuple[int, bool]:
    diagnostics = _batch_diagnostics(response)
    candidates = [
        diagnostics.get("related_total"),
        diagnostics.get("total_related"),
        diagnostics.get("total_relacionados"),
        diagnostics.get("related_total_count"),
        diagnostics.get("related_count"),
        diagnostics.get("total"),
        diagnostics.get("total_count"),
    ]
    for value in candidates:
        try:
            if value is not None:
                total = int(value)
                returned = _returned_count(response)
                if _has_more_pages(response) and total <= returned:
                    return total, False
                return total, True
        except (TypeError, ValueError):
            pass
    return len(_iter_batch_related(response)), False


def _returned_count(response: dict[str, Any]) -> int:
    diagnostics = _batch_diagnostics(response)
    candidates = [diagnostics.get("returned_count"), diagnostics.get("count")]
    for value in candidates:
        try:
            if value is not None:
                return int(value)
        except (TypeError, ValueError):
            pass
    return len(_iter_batch_related(response))


def _has_more_pages(response: dict[str, Any]) -> bool:
    diagnostics = _batch_diagnostics(response)
    if "has_more_pages" in diagnostics:
        return bool(diagnostics.get("has_more_pages"))
    meta = response.get("meta")
    if isinstance(meta, dict):
        try:
            page = int(meta.get("page") or 1)
            last_page = int(meta.get("last_page") or page)
            return page < last_page
        except (TypeError, ValueError):
            pass
    return False


def _chunks(values: list[int], size: int) -> list[list[int]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def _iter_batch_related(response: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    data = response.get("data", [])
    related: list[tuple[int, dict[str, Any]]] = []

    if isinstance(data, dict):
        for master_id, documents in data.items():
            related.extend((int(master_id), document) for document in _as_document_list(documents))
        return related

    for item in data:
        if not isinstance(item, dict):
            continue
        documents = (
            item.get("documents")
            or item.get("related")
            or item.get("relacionados")
            or item.get("items")
            or item.get("data")
        )
        if documents is not None:
            master_id = int(item.get("master_id") or item.get("iddocumento") or item.get("document_id"))
            related.extend((master_id, document) for document in _as_document_list(documents))
            continue
        document = item.get("document") or item.get("documento")
        if isinstance(document, dict):
            master_id = item.get("master_id") or item.get("document_id") or item.get("oper_iddocumento_adj")
            if master_id is not None:
                related.append((int(master_id), document))
            continue
        master_id = item.get("master_id") or item.get("document_id") or item.get("oper_iddocumento_adj")
        if master_id is not None:
            related.append((int(master_id), item))

    return related


def _batch_diagnostics(response: dict[str, Any]) -> dict[str, Any]:
    diagnostics: dict[str, Any] = {}
    meta = response.get("meta")
    if isinstance(meta, dict):
        diagnostics.update(meta)
    for key in (
        "masters",
        "masters_count",
        "related_count",
        "related_total",
        "total_related",
        "total_relacionados",
        "related_total_count",
        "returned_count",
        "count",
        "page",
        "per_page",
        "has_more_pages",
        "missing_master_id",
        "mismatched_relation",
        "has_files_arrays",
    ):
        if key in response:
            diagnostics[key] = response[key]
    return diagnostics


def _response_keys(response: dict[str, Any]) -> str:
    data = response.get("data")
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return ", ".join(sorted(str(key) for key in data[0].keys()))
    if isinstance(data, dict):
        return f"data: {', '.join(sorted(str(key) for key in data.keys())[:10])}"
    return ", ".join(sorted(str(key) for key in response.keys()))


def _as_document_list(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        document = value.get("document") or value.get("documento")
        if isinstance(document, dict):
            return [document]
        return [value]
    return []


def run_file_download(
    options: DownloadOptions,
    log: Callable[[str], None],
    stopped: Callable[[], bool] | None = None,
    progress: Callable[[int, int, str], None] | None = None,
) -> FileDownloadStats:
    """Downloads attachments already recorded locally without re-querying document lists."""
    db_path = database_path(options.output_dir)
    if not db_path.exists():
        raise SgdApiError("No existe una base local para el contexto seleccionado.")

    sources = file_download_sources(
        db_path,
        period=options.period,
        scope=options.scope,
        depe_id=options.depe_id,
    )
    tasks = _file_tasks(options.output_dir, sources, options.group_size)
    upsert_file_download_tasks(options.output_dir, tasks)
    stats = FileDownloadStats(files_total=len(tasks))
    stats.catalog_file = options.output_dir / "descargas_archivos.sqlite"
    if not tasks:
        log("No hay archivos adjuntos registrados para descargar.")
        if progress:
            progress(0, 0, "Sin archivos adjuntos")
        return stats

    client = SgdApiClient(options.service_url, token=options.token, timeout=120)
    log(f"Catalogo actualizado: {len(tasks)} archivos.")
    processed = 0
    for task in tasks:
        if stopped and stopped():
            log("Descarga de archivos cancelada por el usuario.")
            break
        destination = options.output_dir / task["relative_path"]
        file_data = task["file_data"]
        try:
            if should_skip(destination, file_data):
                stats.files_skipped += 1
                mark_file_download(options.output_dir, task["relative_path"], status="descargado")
                log(f"  Omitido: {task['relative_path']}")
            else:
                client.download_file(
                    task["file_id"],
                    destination,
                    scope=options.scope,
                    depe_id=options.depe_id,
                    master_id=task["master_id"],
                )
                stats.files_downloaded += 1
                mark_file_download(
                    options.output_dir,
                    task["relative_path"],
                    status="descargado",
                    attempted=True,
                )
                log(f"  Descargado: {task['relative_path']}")
        except (SgdApiError, OSError) as exc:
            stats.files_failed += 1
            mark_file_download(
                options.output_dir,
                task["relative_path"],
                status="error",
                error=str(exc),
                attempted=True,
            )
            log(f"  Error {task['file_id']}: {exc}")
        processed += 1
        if progress:
            progress(processed, stats.files_total, "Descargando archivos")
    return stats


def _file_tasks(
    output_dir: Path,
    sources: list[tuple[dict[str, Any], int | None, dict[str, Any]]],
    group_size: int,
) -> list[dict[str, Any]]:
    tasks_by_path: dict[str, dict[str, Any]] = {}
    for document, master_id, master_document in sources:
        files = document.get("files") or []
        if not isinstance(files, list):
            continue
        folder = document_folder(output_dir, master_document, group_size)
        prefix = document_name(document) if master_id is not None else None
        document_id = _document_identifier(document)
        if document_id is None:
            continue
        for file_data in files:
            if not isinstance(file_data, dict):
                continue
            file_id = _file_identifier(file_data)
            if file_id is None:
                continue
            name = file_name(file_data, prefix)
            relative_path = str((folder / name).relative_to(output_dir))
            existing = tasks_by_path.get(relative_path)
            if existing and existing["file_id"] != file_id:
                name_path = Path(name)
                name = f"{name_path.stem}_{file_id}{name_path.suffix}"
                relative_path = str((folder / name).relative_to(output_dir))
            tasks_by_path[relative_path] = {
                "relative_path": relative_path,
                "file_id": file_id,
                "document_id": document_id,
                "master_id": master_id,
                "file_name": name,
                "mime_type": str(file_data.get("file_tipo") or file_data.get("mime_type") or ""),
                "expected_size": expected_size(file_data),
                "file_data": file_data,
            }
    return [tasks_by_path[key] for key in sorted(tasks_by_path)]


def _file_identifier(file_data: dict[str, Any]) -> int | None:
    for key in ("id", "idfile", "file_id", "archivo_id"):
        try:
            value = file_data.get(key)
            if value is not None and str(value).strip():
                return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _document_identifier(document: dict[str, Any]) -> int | None:
    for key in ("iddocumento", "document_id", "id_documento", "docu_id", "id"):
        try:
            value = document.get(key)
            if value is not None and str(value).strip():
                return int(value)
        except (TypeError, ValueError):
            continue
    return None
