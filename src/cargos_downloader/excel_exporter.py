from __future__ import annotations

import json
import re
import sqlite3
import zipfile
from collections import defaultdict
from contextlib import closing
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from cargos_downloader.storage import init_database, safe_path_segment


REPORT_COLUMNS = [
    "N. Documento",
    "Firmante",
    "Fecha",
    "Asunto",
    "Oficinas destinatarias",
    "Expediente y Documento",
    "Folios",
    "Fisico/Digital",
    "Digital",
    "Observaciones",
    "Relacionados",
    "CUI",
    "Tipo de trámite",
    "Número correlativo",
    "Reg. SGD",
]


def report_path(output_dir: Path, *, period: int, scope: str, depe_id: int) -> Path:
    return output_dir / f"registro_documentos_{period}_{scope}_{depe_id}.xlsx"


def manual_report_path(output_dir: Path, *, period: int, scope: str, depe_id: int) -> Path:
    return output_dir / f"registro_documentos_manuales_externos_{period}_{scope}_{depe_id}.xlsx"


def personal_report_path(
    output_dir: Path,
    *,
    period: int,
    scope: str,
    depe_id: int,
    user_id: str,
    signer: str,
) -> Path:
    safe_user_id = safe_path_segment(user_id, "sin_id")
    safe_signer = safe_path_segment(signer, "sin_firmante")[:80]
    return output_dir / (
        f"registro_documentos_personales_usuario_{safe_user_id}_{safe_signer}_"
        f"{period}_{scope}_{depe_id}.xlsx"
    )


def export_report(db_path: Path, output_file: Path, *, period: int, scope: str, depe_id: int) -> int:
    init_database(db_path)
    rows = _load_rows(db_path, period=period, scope=scope, depe_id=depe_id)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    sheets = _build_sheets(rows, period)
    _write_xlsx(output_file, sheets)
    return len(rows)


def export_report_files(
    db_path: Path,
    output_dir: Path,
    *,
    period: int,
    scope: str,
    depe_id: int,
    separate_personal: bool = False,
) -> list[tuple[Path, int]]:
    output_file = report_path(output_dir, period=period, scope=scope, depe_id=depe_id)
    if not separate_personal or scope != "oficina":
        count = export_report(
            db_path,
            output_file,
            period=period,
            scope=scope,
            depe_id=depe_id,
        )
        return [(output_file, count)]

    init_database(db_path)
    rows = _load_rows(db_path, period=period, scope=scope, depe_id=depe_id)
    classified: list[tuple[sqlite3.Row, tuple[str, str | None]]] = []
    classification_issues: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        classification, issue = _document_classification(row)
        if issue:
            classification_issues[issue].append(int(row["iddocumento"]))
        elif classification:
            classified.append((row, classification))
    if classification_issues:
        raise ValueError(_classification_error_message(classification_issues))

    office_rows = [row for row, classification in classified if classification == ("office", None)]
    external_rows = [
        row for row, classification in classified if classification == ("external", None)
    ]
    personal_rows: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row, classification in classified:
        if classification and classification[0] == "personal":
            personal_rows[classification[1] or ""].append(row)

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_xlsx(output_file, _build_sheets(office_rows, period))
    reports = [(output_file, len(office_rows))]

    manual_file = manual_report_path(
        output_dir,
        period=period,
        scope=scope,
        depe_id=depe_id,
    )
    _write_xlsx(manual_file, _build_sheets(external_rows, period))
    reports.append((manual_file, len(external_rows)))

    for user_id in sorted(personal_rows, key=lambda value: (value.casefold(), value)):
        user_rows = personal_rows[user_id]
        signer = _personal_signer(user_rows)
        personal_file = personal_report_path(
            output_dir,
            period=period,
            scope=scope,
            depe_id=depe_id,
            user_id=user_id,
            signer=signer,
        )
        _write_xlsx(personal_file, _build_sheets(user_rows, period))
        reports.append((personal_file, len(user_rows)))
    return reports


def preview_sheets(
    db_path: Path,
    *,
    period: int,
    scope: str,
    depe_id: int,
    limit_per_sheet: int = 300,
) -> list[tuple[str, int, list[list[object]]]]:
    init_database(db_path)
    groups = _load_preview_groups(
        db_path,
        period=period,
        scope=scope,
        depe_id=depe_id,
        limit_per_sheet=limit_per_sheet,
    )
    if not groups:
        return [("Sin registros", 0, [["ID", *REPORT_COLUMNS]])]
    preview: list[tuple[str, int, list[list[object]]]] = []
    for name, _, total, grouped_rows in groups:
        data_rows = [[row["iddocumento"], *_report_row(row)] for row in grouped_rows]
        preview.append((name, total, [["ID", *REPORT_COLUMNS], *data_rows]))
    return preview


def related_preview_rows(
    db_path: Path,
    *,
    master_id: int,
    period: int,
    scope: str,
    depe_id: int,
    limit: int | None = None,
) -> list[list[object]]:
    init_database(db_path)
    limit_sql = "" if limit is None else " LIMIT ?"
    params: tuple[object, ...] = (period, scope, depe_id, master_id)
    if limit is not None:
        params = (*params, limit)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = list(
            connection.execute(
                f"""
                SELECT d.iddocumento, d.document_type, d.document_number, d.document_acronyms,
                       d.document_date,
                       d.signer, d.subject, d.addressee, d.expediente_documento,
                       d.folios, d.storage_type, d.observations
                FROM document_relations AS rel
                JOIN documents AS d
                  ON d.iddocumento = rel.related_id
                 AND d.period = rel.period
                 AND d.scope = rel.scope
                 AND d.depe_id = rel.depe_id
                WHERE rel.period = ? AND rel.scope = ? AND rel.depe_id = ?
                  AND rel.master_id = ?
                ORDER BY d.document_type COLLATE NOCASE, d.document_date, d.document_number
                {limit_sql}
                """,
                params,
            )
        )
    header = [
        "Tipo",
        "N. Documento",
        "Firmante",
        "Fecha",
        "Asunto",
        "Dirigido a",
        "Expediente y Documento",
        "Folios",
        "Fisico/Digital",
        "Digital",
        "Observaciones",
        "Número correlativo",
        "Reg. SGD",
    ]
    data = [
        [
            row["document_type"] or "",
            _full_document_number(row),
            row["signer"] or "",
            _format_date(row["document_date"]),
            row["subject"] or "",
            row["addressee"] or "",
            row["expediente_documento"] or "",
            row["folios"] or "",
            row["storage_type"] or "",
            "",
            row["observations"] or "",
            row["document_number"] or "",
            row["iddocumento"],
        ]
        for row in rows
    ]
    return [header, *data]


def related_count(db_path: Path, *, master_id: int, period: int, scope: str, depe_id: int) -> int:
    init_database(db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        value = connection.execute(
            """
            SELECT COUNT(*)
            FROM document_relations
            WHERE period = ? AND scope = ? AND depe_id = ? AND master_id = ?
            """,
            (period, scope, depe_id, master_id),
        ).fetchone()[0]
    return int(value or 0)


def _load_rows(db_path: Path, *, period: int, scope: str, depe_id: int) -> list[sqlite3.Row]:
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        return list(
            connection.execute(
                """
                SELECT p.iddocumento, p.document_type, p.document_number, p.document_acronyms,
                       p.document_date,
                       p.signer, p.subject, p.recipient_offices, p.expediente_documento, p.folios,
                       p.storage_type, p.observations, COUNT(rel.related_id) AS related_count,
                       p.project_cui, p.procedure_type_description, p.raw_json
                FROM documents AS p
                LEFT JOIN document_relations AS rel
                  ON rel.master_id = p.iddocumento
                 AND rel.period = p.period
                 AND rel.scope = p.scope
                 AND rel.depe_id = p.depe_id
                WHERE p.period = ? AND p.scope = ? AND p.depe_id = ?
                  AND p.relation_kind = 'principal'
                GROUP BY p.iddocumento
                ORDER BY p.document_type COLLATE NOCASE, p.document_date, p.document_number
                """,
                (period, scope, depe_id),
            )
        )


def _document_classification(
    row: sqlite3.Row,
) -> tuple[tuple[str, str | None] | None, str | None]:
    try:
        document = json.loads(row["raw_json"])
    except (KeyError, TypeError, json.JSONDecodeError):
        return None, "JSON original inválido"
    if not isinstance(document, dict):
        return None, "JSON original no es un objeto"

    origin_value = document.get("docu_origen")
    if origin_value is None or not str(origin_value).strip():
        return None, "docu_origen ausente o vacío"
    try:
        origin = int(origin_value)
    except (TypeError, ValueError):
        return None, "docu_origen no es numérico"
    if origin in (2, 3):
        return ("external", None), None
    if origin != 1:
        return None, f"docu_origen no reconocido ({origin})"

    if "docu_tipo" not in document:
        return None, "docu_tipo ausente para docu_origen=1"
    kind_value = document["docu_tipo"]
    if kind_value is None:
        kind = 0
    else:
        if not str(kind_value).strip():
            return None, "docu_tipo vacío para docu_origen=1"
        try:
            kind = int(kind_value)
        except (TypeError, ValueError):
            return None, "docu_tipo no es numérico para docu_origen=1"
    if kind == 0:
        return ("office", None), None
    if kind != 1:
        return None, f"docu_tipo no reconocido ({kind}) para docu_origen=1"

    user_id = document.get("docu_idusuario")
    user_id_field = "docu_idusuario"
    if user_id is None:
        user_id = document.get("oper_idusuario")
        user_id_field = "oper_idusuario"
    if user_id is None or not str(user_id).strip():
        return None, (
            "docu_idusuario y oper_idusuario ausentes o vacíos en documento personal"
        )
    if isinstance(user_id, bool):
        return None, f"{user_id_field} no es un identificador válido"
    try:
        user_id_number = int(user_id)
    except (TypeError, ValueError):
        return None, f"{user_id_field} no es numérico en documento personal"
    if user_id_number <= 0:
        return None, f"{user_id_field} no es positivo en documento personal"
    return ("personal", str(user_id_number)), None


def _classification_error_message(issues: dict[str, list[int]]) -> str:
    total = sum(len(document_ids) for document_ids in issues.values())
    lines = [
        f"No se pudo exportar: {total} documento(s) tienen datos de clasificación inválidos.",
        "",
        "Detalle:",
    ]
    for reason, document_ids in issues.items():
        sample = ", ".join(str(document_id) for document_id in document_ids[:10])
        remaining = len(document_ids) - 10
        suffix = f" y {remaining} más" if remaining > 0 else ""
        lines.append(
            f"- {reason}: {len(document_ids)}. Reg. SGD: {sample}{suffix}."
        )
    lines.extend(
        [
            "",
            "Vuelva a descargar los registros si el SGD ya corrigió esos campos.",
            "Este detalle también se guardó en Detalle de acciones y app.log.",
        ]
    )
    return "\n".join(lines)


def _personal_signer(rows: list[sqlite3.Row]) -> str:
    names = sorted(
        {str(row["signer"]).strip() for row in rows if str(row["signer"] or "").strip()},
        key=str.casefold,
    )
    return names[0] if names else "sin_firmante"


def _load_preview_groups(
    db_path: Path,
    *,
    period: int,
    scope: str,
    depe_id: int,
    limit_per_sheet: int,
) -> list[tuple[str, str, int, list[sqlite3.Row]]]:
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        counts = list(
            connection.execute(
                """
                SELECT document_type, COUNT(*) AS total
                FROM documents
                WHERE period = ? AND scope = ? AND depe_id = ?
                  AND relation_kind = 'principal'
                GROUP BY document_type
                ORDER BY document_type COLLATE NOCASE
                """,
                (period, scope, depe_id),
            )
        )
        used_names: set[str] = set()
        groups = []
        for count_row in counts:
            document_type = count_row["document_type"] or "SIN TIPO"
            total = int(count_row["total"] or 0)
            rows = list(
                connection.execute(
                    """
                    WITH related_counts AS (
                        SELECT master_id, COUNT(*) AS related_count
                        FROM document_relations
                        WHERE period = ? AND scope = ? AND depe_id = ?
                        GROUP BY master_id
                    )
                    SELECT p.iddocumento, p.document_type, p.document_number, p.document_acronyms,
                           p.document_date,
                           p.signer, p.subject, p.recipient_offices, p.expediente_documento, p.folios,
                           p.storage_type, p.observations,
                           COALESCE(rc.related_count, 0) AS related_count,
                           p.project_cui, p.procedure_type_description
                    FROM documents AS p
                    LEFT JOIN related_counts AS rc ON rc.master_id = p.iddocumento
                    WHERE p.period = ? AND p.scope = ? AND p.depe_id = ?
                      AND p.relation_kind = 'principal' AND p.document_type = ?
                    ORDER BY p.document_date, p.document_number
                    LIMIT ?
                    """,
                    (
                        period,
                        scope,
                        depe_id,
                        period,
                        scope,
                        depe_id,
                        document_type,
                        max(1, limit_per_sheet),
                    ),
                )
            )
            name = _unique_sheet_name(f"{period} {_clean_sheet_name(document_type)}", used_names)
            groups.append((name, document_type, total, rows))
    return groups


def _build_sheets(rows: list[sqlite3.Row], period: int) -> list[tuple[str, list[list[object]], list[tuple[int, int, str]]]]:
    grouped = _group_rows(rows, period)
    if not grouped:
        return [("Sin registros", _sheet_rows("SIN REGISTROS", period, []), [(1, 1, "O1"), (3, 3, "O3")])]

    sheets = [(name, _sheet_rows(document_type, period, grouped_rows), [(1, 1, "O1"), (3, 3, "O3")]) for name, document_type, grouped_rows in grouped]
    return sheets


def _group_rows(rows: list[sqlite3.Row], period: int) -> list[tuple[str, str, list[sqlite3.Row]]]:
    grouped: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        grouped[row["document_type"] or "SIN TIPO"].append(row)

    result = []
    used_names: set[str] = set()
    for document_type in sorted(grouped, key=str.casefold):
        name = _unique_sheet_name(f"{period} {_clean_sheet_name(document_type)}", used_names)
        result.append((name, document_type, grouped[document_type]))
    return result


def _sheet_rows(document_type: str, period: int, rows: list[sqlite3.Row]) -> list[list[object]]:
    data: list[list[object]] = [
        ["REGISTRO DE DOCUMENTOS", "", "", "", "", "", "", "", ""],
        [f"Periodo: {period}", "", "", "", "", "", "", "Pag.", ""],
        [f"1. Tipo: {document_type}", "", "", "", "", "", "", "", ""],
        REPORT_COLUMNS,
    ]
    for row in rows:
        data.append(_report_row(row))
    return data


def _report_row(row: sqlite3.Row) -> list[object]:
    return [
        _full_document_number(row),
        row["signer"] or "",
        _format_date(row["document_date"]),
        row["subject"] or "",
        row["recipient_offices"] or "",
        row["expediente_documento"] or "",
        row["folios"] or "",
        row["storage_type"] or "",
        "",
        row["observations"] or "",
        row["related_count"] or "",
        row["project_cui"] or "",
        row["procedure_type_description"] or "",
        row["document_number"] or "",
        row["iddocumento"],
    ]


def _write_xlsx(
    output_file: Path,
    sheets: list[tuple[str, list[list[object]], list[tuple[int, int, str]]]],
) -> None:
    with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types(len(sheets)))
        archive.writestr("_rels/.rels", _root_rels())
        archive.writestr("xl/workbook.xml", _workbook_xml(sheets))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels(len(sheets)))
        archive.writestr("xl/styles.xml", _styles_xml())
        for index, (_, rows, merges) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _worksheet_xml(rows, merges))


def _worksheet_xml(rows: list[list[object]], merges: list[tuple[int, int, str]]) -> str:
    xml_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row, start=1):
            if value == "" and row_index < 4:
                continue
            style = "1" if row_index == 1 else "2" if row_index == 4 else "3" if row_index <= 3 else "4"
            cells.append(_cell_xml(row_index, col_index, value, style))
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    merge_xml = ""
    if merges:
        entries = "".join(f'<mergeCell ref="{ref}"/>' for _, _, ref in merges)
        merge_xml = f'<mergeCells count="{len(merges)}">{entries}</mergeCells>'

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
        '<sheetFormatPr defaultRowHeight="18"/>'
        '<cols>'
        '<col min="1" max="1" width="45" customWidth="1"/>'
        '<col min="2" max="2" width="45" customWidth="1"/>'
        '<col min="3" max="3" width="18" customWidth="1"/>'
        '<col min="4" max="4" width="65" customWidth="1"/>'
        '<col min="5" max="5" width="48" customWidth="1"/>'
        '<col min="6" max="6" width="28" customWidth="1"/>'
        '<col min="7" max="7" width="10" customWidth="1"/>'
        '<col min="8" max="8" width="10" customWidth="1"/>'
        '<col min="9" max="9" width="16" customWidth="1"/>'
        '<col min="10" max="10" width="28" customWidth="1"/>'
        '<col min="11" max="11" width="12" customWidth="1"/>'
        '<col min="12" max="12" width="14" customWidth="1"/>'
        '<col min="13" max="13" width="28" customWidth="1"/>'
        '<col min="14" max="14" width="18" customWidth="1"/>'
        '<col min="15" max="15" width="14" customWidth="1"/>'
        '</cols>'
        f'<sheetData>{"".join(xml_rows)}</sheetData>'
        f"{merge_xml}"
        '<pageMargins left="0.25" right="0.25" top="0.5" bottom="0.5" header="0.3" footer="0.3"/>'
        '<pageSetup orientation="landscape" paperSize="9" fitToWidth="1" fitToHeight="0"/>'
        '</worksheet>'
    )


def _cell_xml(row: int, col: int, value: object, style: str) -> str:
    ref = f"{_column_name(col)}{row}"
    text = escape(str(value))
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t>{text}</t></is></c>'


def _content_types(sheet_count: int) -> str:
    sheets = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        f"{sheets}</Types>"
    )


def _root_rels() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '</Relationships>'
    )


def _workbook_xml(sheets: list[tuple[str, list[list[object]], list[tuple[int, int, str]]]]) -> str:
    sheet_xml = "".join(
        f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, (name, _, _) in enumerate(sheets, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheet_xml}</sheets>"
        '</workbook>'
    )


def _workbook_rels(sheet_count: int) -> str:
    rels = "".join(
        f'<Relationship Id="rId{i}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, sheet_count + 1)
    )
    style_id = sheet_count + 1
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{rels}"
        f'<Relationship Id="rId{style_id}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
        '</Relationships>'
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="3">'
        '<font><sz val="10"/><name val="Arial"/></font>'
        '<font><b/><sz val="12"/><name val="Arial"/></font>'
        '<font><b/><sz val="10"/><name val="Arial"/></font>'
        '</fonts>'
        '<fills count="3"><fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFEDEDED"/><bgColor indexed="64"/></patternFill></fill></fills>'
        '<borders count="2"><border><left/><right/><top/><bottom/><diagonal/></border>'
        '<border><left style="thin"/><right style="thin"/><top style="thin"/><bottom style="thin"/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="5">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="center"/></xf>'
        '<xf numFmtId="0" fontId="2" fillId="2" borderId="1" xfId="0" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
        '</cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _clean_sheet_name(value: str) -> str:
    cleaned = re.sub(r"[\[\]:*?/\\]", " ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:24] or "SIN TIPO"


def _unique_sheet_name(value: str, used_names: set[str]) -> str:
    base = value[:31]
    name = base
    counter = 2
    while name in used_names:
        suffix = f" {counter}"
        name = f"{base[:31 - len(suffix)]}{suffix}"
        counter += 1
    used_names.add(name)
    return name


def _format_date(value: str | None) -> str:
    if not value:
        return ""
    text = str(value)[:10]
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return text


def _full_document_number(row: sqlite3.Row) -> str:
    number = str(row["document_number"] or "")
    document_type = str(row["document_type"] or "").strip()
    acronyms = str(row["document_acronyms"] or "").strip()
    date_text = str(row["document_date"] or "").strip()
    year_match = re.match(r"^(\d{4})", date_text)
    if not number or not document_type or not acronyms or not year_match:
        return number
    return f"{document_type} {number}-{year_match.group(1)}-{acronyms}"


def _record_type(value: str | None) -> str:
    return "Relacionado" if value == "relacionado" else "Principal"
