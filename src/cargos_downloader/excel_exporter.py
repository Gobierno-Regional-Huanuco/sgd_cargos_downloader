from __future__ import annotations

import re
import sqlite3
import zipfile
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from cargos_downloader.classification import (
    EXTERNAL_ORIGINS,
    ORIGIN_LABELS,
    ORIGIN_UNCLASSIFIED,
    registrant_label,
)
from cargos_downloader.storage import init_database, registrant_names


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
    "Origen",
    "Registrado por",
    "Reg. SGD",
]
EXTERNAL_REPORT_COLUMNS = ["Tipo", *REPORT_COLUMNS]

COLUMN_WIDTHS = {
    "Tipo": 24,
    "N. Documento": 45,
    "Firmante": 45,
    "Fecha": 18,
    "Asunto": 65,
    "Oficinas destinatarias": 48,
    "Expediente y Documento": 28,
    "Folios": 10,
    "Fisico/Digital": 10,
    "Digital": 16,
    "Observaciones": 28,
    "Relacionados": 12,
    "CUI": 14,
    "Tipo de trámite": 28,
    "Número correlativo": 18,
    "Origen": 22,
    "Registrado por": 36,
    "Reg. SGD": 14,
}

HEADER_ROW = 4
EXTERNAL_SHEET_LABEL = "EXTERNOS"
_EXTERNAL_SQL = "(" + ", ".join(f"'{origin}'" for origin in sorted(EXTERNAL_ORIGINS)) + ")"

_PRINCIPAL_COLUMNS_SQL = """
    p.iddocumento, p.document_type, p.document_number, p.document_acronyms,
    p.document_date, p.signer, p.subject, p.recipient_offices, p.expediente_documento,
    p.folios, p.storage_type, p.observations, p.project_cui, p.procedure_type_description,
    p.origin_group, p.registrant_id, p.classification_issue
"""

Sheet = tuple[str, list[list[object]]]


@dataclass
class ExportResult:
    output_file: Path
    records: int
    external_records: int = 0
    unclassified: dict[str, list[int]] = field(default_factory=dict)


def report_path(output_dir: Path, *, period: int, scope: str, depe_id: int) -> Path:
    return output_dir / f"registro_documentos_{period}_{scope}_{depe_id}.xlsx"


def export_report(
    db_path: Path,
    output_file: Path,
    *,
    period: int,
    scope: str,
    depe_id: int,
) -> ExportResult:
    """Genera un unico libro: hojas por tipo y una hoja de externos.

    Oficina, personales y documentos sin clasificar comparten las hojas por
    tipo y se distinguen con las columnas Origen y Registrado por. Los
    clasificados como manuales/externos o PIDE van a la hoja de externos.
    """
    init_database(db_path)
    rows = _load_rows(db_path, period=period, scope=scope, depe_id=depe_id)
    names = registrant_names(db_path, period=period, scope=scope, depe_id=depe_id)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    _write_xlsx(output_file, _build_sheets(rows, period, names))

    unclassified: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        if _origin_group(row) == ORIGIN_UNCLASSIFIED:
            reason = row["classification_issue"] or "clasificación no disponible"
            unclassified[reason].append(int(row["iddocumento"]))
    return ExportResult(
        output_file=output_file,
        records=len(rows),
        external_records=sum(1 for row in rows if _is_external(row)),
        unclassified=dict(unclassified),
    )


def classification_warning_message(issues: dict[str, list[int]]) -> str:
    total = sum(len(document_ids) for document_ids in issues.values())
    lines = [
        f"{total} documento(s) se exportaron con Origen \"Sin clasificar\" "
        "porque el SGD no envió datos de clasificación válidos.",
        "",
        "Detalle:",
    ]
    for reason, document_ids in issues.items():
        sample = ", ".join(str(document_id) for document_id in document_ids[:10])
        remaining = len(document_ids) - 10
        suffix = f" y {remaining} más" if remaining > 0 else ""
        lines.append(f"- {reason}: {len(document_ids)}. Reg. SGD: {sample}{suffix}.")
    lines.extend(
        [
            "",
            "Puede filtrarlos en la columna Origen. Vuelva a descargar los registros "
            "si el SGD ya corrigió esos campos.",
            "Este detalle también se guardó en Detalle de acciones y app.log.",
        ]
    )
    return "\n".join(lines)


def preview_sheets(
    db_path: Path,
    *,
    period: int,
    scope: str,
    depe_id: int,
    limit_per_sheet: int = 300,
) -> list[tuple[str, int, list[list[object]]]]:
    init_database(db_path)
    names = registrant_names(db_path, period=period, scope=scope, depe_id=depe_id)
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
    for name, external, total, grouped_rows in groups:
        columns = EXTERNAL_REPORT_COLUMNS if external else REPORT_COLUMNS
        data_rows = [
            [row["iddocumento"], *_report_row(row, names, include_type=external)]
            for row in grouped_rows
        ]
        preview.append((name, total, [["ID", *columns], *data_rows]))
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
                f"""
                WITH related_counts AS (
                    SELECT master_id, COUNT(*) AS related_count
                    FROM document_relations
                    WHERE period = ? AND scope = ? AND depe_id = ?
                    GROUP BY master_id
                )
                SELECT {_PRINCIPAL_COLUMNS_SQL},
                       COALESCE(rc.related_count, 0) AS related_count
                FROM documents AS p
                LEFT JOIN related_counts AS rc ON rc.master_id = p.iddocumento
                WHERE p.period = ? AND p.scope = ? AND p.depe_id = ?
                  AND p.relation_kind = 'principal'
                ORDER BY p.document_type COLLATE NOCASE, p.document_date, p.document_number
                """,
                (period, scope, depe_id, period, scope, depe_id),
            )
        )


def _load_preview_groups(
    db_path: Path,
    *,
    period: int,
    scope: str,
    depe_id: int,
    limit_per_sheet: int,
) -> list[tuple[str, bool, int, list[sqlite3.Row]]]:
    external_expr = f"COALESCE(origin_group, '') IN {_EXTERNAL_SQL}"
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        counts = list(
            connection.execute(
                f"""
                SELECT document_type, COUNT(*) AS total
                FROM documents
                WHERE period = ? AND scope = ? AND depe_id = ?
                  AND relation_kind = 'principal' AND NOT {external_expr}
                GROUP BY document_type
                ORDER BY document_type COLLATE NOCASE
                """,
                (period, scope, depe_id),
            )
        )
        external_total = int(
            connection.execute(
                f"""
                SELECT COUNT(*)
                FROM documents
                WHERE period = ? AND scope = ? AND depe_id = ?
                  AND relation_kind = 'principal' AND {external_expr}
                """,
                (period, scope, depe_id),
            ).fetchone()[0]
            or 0
        )

        def load(condition: str, extra: tuple[object, ...]) -> list[sqlite3.Row]:
            return list(
                connection.execute(
                    f"""
                    WITH related_counts AS (
                        SELECT master_id, COUNT(*) AS related_count
                        FROM document_relations
                        WHERE period = ? AND scope = ? AND depe_id = ?
                        GROUP BY master_id
                    )
                    SELECT {_PRINCIPAL_COLUMNS_SQL},
                           COALESCE(rc.related_count, 0) AS related_count
                    FROM documents AS p
                    LEFT JOIN related_counts AS rc ON rc.master_id = p.iddocumento
                    WHERE p.period = ? AND p.scope = ? AND p.depe_id = ?
                      AND p.relation_kind = 'principal' AND {condition}
                    ORDER BY p.document_type COLLATE NOCASE, p.document_date, p.document_number
                    LIMIT ?
                    """,
                    (
                        period,
                        scope,
                        depe_id,
                        period,
                        scope,
                        depe_id,
                        *extra,
                        max(1, limit_per_sheet),
                    ),
                )
            )

        external_name = _external_sheet_name(period)
        used_names: set[str] = {external_name}
        groups = []
        for count_row in counts:
            document_type = count_row["document_type"] or "SIN TIPO"
            rows = load(
                f"NOT COALESCE(p.origin_group, '') IN {_EXTERNAL_SQL} AND p.document_type = ?",
                (document_type,),
            )
            name = _unique_sheet_name(f"{period} {_clean_sheet_name(document_type)}", used_names)
            groups.append((name, False, int(count_row["total"] or 0), rows))
        if external_total:
            rows = load(f"COALESCE(p.origin_group, '') IN {_EXTERNAL_SQL}", ())
            groups.append((external_name, True, external_total, rows))
    return groups


def _build_sheets(rows: list[sqlite3.Row], period: int, names: dict[str, str]) -> list[Sheet]:
    internal_rows = [row for row in rows if not _is_external(row)]
    external_rows = [row for row in rows if _is_external(row)]
    if not rows:
        return [("Sin registros", _sheet_rows("1. Tipo: SIN REGISTROS", period, [], names))]

    external_name = _external_sheet_name(period)
    used_names: set[str] = {external_name}
    grouped: dict[str, list[sqlite3.Row]] = defaultdict(list)
    for row in internal_rows:
        grouped[row["document_type"] or "SIN TIPO"].append(row)

    sheets: list[Sheet] = []
    for document_type in sorted(grouped, key=str.casefold):
        name = _unique_sheet_name(f"{period} {_clean_sheet_name(document_type)}", used_names)
        sheets.append(
            (name, _sheet_rows(f"1. Tipo: {document_type}", period, grouped[document_type], names))
        )
    if external_rows:
        sheets.append(
            (
                external_name,
                _sheet_rows(
                    "Origen: Manuales/externos e interoperabilidad/PIDE",
                    period,
                    external_rows,
                    names,
                    external=True,
                ),
            )
        )
    return sheets


def _sheet_rows(
    subtitle: str,
    period: int,
    rows: list[sqlite3.Row],
    names: dict[str, str],
    *,
    external: bool = False,
) -> list[list[object]]:
    title = "REGISTRO DE DOCUMENTOS EXTERNOS" if external else "REGISTRO DE DOCUMENTOS"
    data: list[list[object]] = [
        [title],
        [f"Periodo: {period}", "", "", "", "", "", "", "Pag."],
        [subtitle],
        EXTERNAL_REPORT_COLUMNS if external else REPORT_COLUMNS,
    ]
    for row in rows:
        data.append(_report_row(row, names, include_type=external))
    return data


def _report_row(row: sqlite3.Row, names: dict[str, str], *, include_type: bool = False) -> list[object]:
    values: list[object] = [
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
        ORIGIN_LABELS[_origin_group(row)],
        registrant_label(row["registrant_id"], names),
        row["iddocumento"],
    ]
    if include_type:
        values.insert(0, row["document_type"] or "")
    return values


def _origin_group(row: sqlite3.Row) -> str:
    group = row["origin_group"]
    return group if group in ORIGIN_LABELS else ORIGIN_UNCLASSIFIED


def _is_external(row: sqlite3.Row) -> bool:
    return _origin_group(row) in EXTERNAL_ORIGINS


def _external_sheet_name(period: int) -> str:
    return f"{period} {EXTERNAL_SHEET_LABEL}"


def _write_xlsx(output_file: Path, sheets: list[Sheet]) -> None:
    with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types(len(sheets)))
        archive.writestr("_rels/.rels", _root_rels())
        archive.writestr("xl/workbook.xml", _workbook_xml(sheets))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels(len(sheets)))
        archive.writestr("xl/styles.xml", _styles_xml())
        for index, (_, rows) in enumerate(sheets, start=1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _worksheet_xml(rows))


def _filter_range(rows: list[list[object]]) -> str:
    last_column = _column_name(len(rows[HEADER_ROW - 1]))
    last_row = max(HEADER_ROW, len(rows))
    return f"A{HEADER_ROW}:{last_column}{last_row}"


def _worksheet_xml(rows: list[list[object]]) -> str:
    header = [str(value) for value in rows[HEADER_ROW - 1]]
    last_column = _column_name(len(header))
    xml_rows = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row, start=1):
            if value == "" and row_index < HEADER_ROW:
                continue
            style = (
                "1"
                if row_index == 1
                else "2"
                if row_index == HEADER_ROW
                else "3"
                if row_index < HEADER_ROW
                else "4"
            )
            cells.append(_cell_xml(row_index, col_index, value, style))
        xml_rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')

    columns_xml = "".join(
        f'<col min="{index}" max="{index}" width="{COLUMN_WIDTHS.get(name, 18)}" customWidth="1"/>'
        for index, name in enumerate(header, start=1)
    )
    merges = [f"A1:{last_column}1", f"A3:{last_column}3"]
    merge_xml = (
        f'<mergeCells count="{len(merges)}">'
        + "".join(f'<mergeCell ref="{ref}"/>' for ref in merges)
        + "</mergeCells>"
    )
    first_data_cell = f"A{HEADER_ROW + 1}"

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<sheetViews><sheetView workbookViewId="0">'
        f'<pane ySplit="{HEADER_ROW}" topLeftCell="{first_data_cell}" activePane="bottomLeft" state="frozen"/>'
        f'<selection pane="bottomLeft" activeCell="{first_data_cell}" sqref="{first_data_cell}"/>'
        "</sheetView></sheetViews>"
        '<sheetFormatPr defaultRowHeight="18"/>'
        f"<cols>{columns_xml}</cols>"
        f'<sheetData>{"".join(xml_rows)}</sheetData>'
        f'<autoFilter ref="{_filter_range(rows)}"/>'
        f"{merge_xml}"
        '<pageMargins left="0.25" right="0.25" top="0.5" bottom="0.5" header="0.3" footer="0.3"/>'
        '<pageSetup orientation="landscape" paperSize="9" fitToWidth="1" fitToHeight="0"/>'
        "</worksheet>"
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
        "</Relationships>"
    )


def _workbook_xml(sheets: list[Sheet]) -> str:
    sheet_xml = "".join(
        f'<sheet name="{escape(name)}" sheetId="{index}" r:id="rId{index}"/>'
        for index, (name, _) in enumerate(sheets, start=1)
    )
    defined_names = "".join(
        '<definedName name="_xlnm._FilterDatabase" '
        f'localSheetId="{index}" hidden="1">'
        f"{escape(_absolute_range(name, rows))}</definedName>"
        for index, (name, rows) in enumerate(sheets)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheet_xml}</sheets>"
        f"<definedNames>{defined_names}</definedNames>"
        "</workbook>"
    )


def _absolute_range(sheet_name: str, rows: list[list[object]]) -> str:
    start, end = _filter_range(rows).split(":")
    quoted = sheet_name.replace("'", "''")

    def absolute(ref: str) -> str:
        match = re.match(r"([A-Z]+)(\d+)", ref)
        assert match
        return f"${match.group(1)}${match.group(2)}"

    return f"'{quoted}'!{absolute(start)}:{absolute(end)}"


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
        "</Relationships>"
    )


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="3">'
        '<font><sz val="10"/><name val="Arial"/></font>'
        '<font><b/><sz val="12"/><name val="Arial"/></font>'
        '<font><b/><sz val="10"/><name val="Arial"/></font>'
        "</fonts>"
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
        "</cellXfs>"
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        "</styleSheet>"
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
