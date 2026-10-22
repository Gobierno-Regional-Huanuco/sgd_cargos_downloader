from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock, patch

from cargos_downloader.api import SgdApiClient
from cargos_downloader.excel_exporter import (
    export_report,
    export_report_files,
    manual_report_path,
    personal_report_path,
    preview_sheets,
    related_preview_rows,
    report_path,
)
from cargos_downloader.storage import (
    SCHEMA_VERSION,
    init_database,
    upsert_documents,
    upsert_related_records,
)


class RecipientOfficesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.db_path = self.root / "cargos.sqlite"

    def test_report_uses_api_text_and_keeps_one_row_per_document(self) -> None:
        offices = "GERENCIA DE ADMINISTRACION, OFICINA DE CONTABILIDAD, OFICINA DE TESORERIA"
        documents = [
            self._document(1, "OFICINA DE TESORERIA"),
            self._document(2, offices),
            self._document(3, None),
            self._document(4),
            self._document(5, ""),
        ]

        saved = upsert_documents(
            self.db_path,
            documents,
            period=2026,
            scope="oficina",
            depe_id=10,
        )

        self.assertEqual(saved, 5)
        sheets = preview_sheets(
            self.db_path,
            period=2026,
            scope="oficina",
            depe_id=10,
        )
        self.assertEqual(len(sheets), 1)
        _name, total, rows = sheets[0]
        self.assertEqual(total, 5)
        self.assertEqual(rows[0][5], "Oficinas destinatarias")
        self.assertEqual(rows[1][5], "OFICINA DE TESORERIA")
        self.assertEqual(rows[2][5], offices)
        self.assertEqual(rows[3][5], "")
        self.assertEqual(rows[4][5], "")
        self.assertEqual(rows[5][5], "")
        for row in rows[1:]:
            self.assertEqual(row[1], row[-2])
            self.assertEqual(row[0], row[-1])

    def test_excel_wraps_and_preserves_long_recipient_text(self) -> None:
        offices = "GERENCIA DE ADMINISTRACION, OFICINA DE CONTABILIDAD, OFICINA DE TESORERIA"
        upsert_documents(
            self.db_path,
            [self._document(1, offices)],
            period=2026,
            scope="oficina",
            depe_id=10,
        )
        output = self.root / "report.xlsx"

        count = export_report(
            self.db_path,
            output,
            period=2026,
            scope="oficina",
            depe_id=10,
        )

        self.assertEqual(count, 1)
        with zipfile.ZipFile(output) as workbook:
            sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
            styles = workbook.read("xl/styles.xml").decode("utf-8")
        self.assertIn(offices, sheet)
        self.assertIn('min="1" max="1" width="45"', sheet)
        self.assertIn('min="2" max="2" width="45"', sheet)
        self.assertIn('min="4" max="4" width="65"', sheet)
        self.assertIn('min="5" max="5" width="48"', sheet)
        self.assertIn('min="7" max="7" width="10"', sheet)
        self.assertIn(
            '<c r="B5" s="4" t="inlineStr"><is><t></t></is></c>',
            sheet,
        )
        self.assertIn(
            '<c r="G5" s="4" t="inlineStr"><is><t></t></is></c>',
            sheet,
        )
        self.assertIn(
            '<c r="M5" s="4" t="inlineStr"><is><t></t></is></c>',
            sheet,
        )
        self.assertIn('wrapText="1"', styles)

    def test_cui_and_procedure_type_precede_correlative_column(self) -> None:
        documents = [
            self._document(1, cui=2468101, procedure_type_id=4, procedure_type="EJECUCION DE OBRA"),
            self._document(2, cui=None, procedure_type_id=None, procedure_type=None),
            self._document(3, cui="", procedure_type_id="", procedure_type=""),
            self._document(4),
            self._document(5, cui=0, procedure_type_id=7, procedure_type="undefined"),
        ]
        upsert_documents(
            self.db_path,
            documents,
            period=2026,
            scope="oficina",
            depe_id=10,
        )

        _name, total, rows = preview_sheets(
            self.db_path,
            period=2026,
            scope="oficina",
            depe_id=10,
        )[0]

        self.assertEqual(total, 5)
        self.assertEqual(
            rows[0],
            [
                "ID",
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
            ],
        )
        self.assertEqual(rows[1][-4:], ["2468101", "EJECUCION DE OBRA", "000001", 1])
        for row in rows[2:]:
            self.assertEqual(row[-4:-2], ["", ""])
        with closing(sqlite3.connect(self.db_path)) as connection:
            stored_id = connection.execute(
                "SELECT procedure_type_id FROM documents WHERE iddocumento = 1"
            ).fetchone()
        self.assertEqual(stored_id, (4,))

        output = self.root / "procedure-report.xlsx"
        exported = export_report(
            self.db_path,
            output,
            period=2026,
            scope="oficina",
            depe_id=10,
        )
        self.assertEqual(exported, 5)
        with zipfile.ZipFile(output) as workbook:
            sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertIn("CUI", sheet)
        self.assertIn("Tipo de trámite", sheet)
        self.assertIn("2468101", sheet)
        self.assertIn("EJECUCION DE OBRA", sheet)
        self.assertIn('min="12" max="12" width="14"', sheet)
        self.assertIn('min="13" max="13" width="28"', sheet)
        self.assertIn('min="15" max="15" width="14"', sheet)
        self.assertIn('mergeCell ref="O1"', sheet)
        self.assertIn('mergeCell ref="O3"', sheet)

    def test_composite_number_and_correlative_apply_to_main_and_related_reports(self) -> None:
        principal = self._document(
            100,
            number=635,
            document_type="MEMORANDUM MULTIPLE",
            document_date="2026-10-20",
            acronyms="GRH/GGR",
        )
        related = self._document(
            101,
            number=27,
            document_type="INFORME",
            document_date="2026-02-03",
            acronyms="GRH/ORA",
        )
        upsert_documents(
            self.db_path,
            [principal],
            period=2026,
            scope="oficina",
            depe_id=10,
        )
        upsert_related_records(
            self.db_path,
            [(related, 100)],
            period=2026,
            scope="oficina",
            depe_id=10,
        )

        main_rows = preview_sheets(
            self.db_path,
            period=2026,
            scope="oficina",
            depe_id=10,
        )[0][2]
        related_rows = related_preview_rows(
            self.db_path,
            master_id=100,
            period=2026,
            scope="oficina",
            depe_id=10,
        )

        self.assertEqual(main_rows[1][1], "MEMORANDUM MULTIPLE 000635-2026-GRH/GGR")
        self.assertEqual(main_rows[1][-2:], ["000635", 100])
        self.assertEqual(related_rows[1][1], "INFORME 000027-2026-GRH/ORA")
        self.assertEqual(related_rows[0][-1], "Reg. SGD")
        self.assertEqual(related_rows[1][-2:], ["000027", 101])

        output = self.root / "numbering-report.xlsx"
        self.assertEqual(
            export_report(
                self.db_path,
                output,
                period=2026,
                scope="oficina",
                depe_id=10,
            ),
            1,
        )
        with zipfile.ZipFile(output) as workbook:
            sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertIn("MEMORANDUM MULTIPLE 000635-2026-GRH/GGR", sheet)
        self.assertIn("Número correlativo", sheet)
        self.assertIn("<t>000635</t>", sheet)
        self.assertIn("Reg. SGD", sheet)
        self.assertIn("<t>100</t>", sheet)

    def test_office_export_separates_office_external_and_each_personal_user(self) -> None:
        upsert_documents(
            self.db_path,
            [
                self._document(201, document_origin=1, document_kind=0),
                self._document(212, document_origin=1, document_kind=None),
                self._document(
                    202,
                    document_origin=1,
                    document_kind=1,
                    document_user_id=30,
                    operation_user_id=999,
                    signer="ANA PEREZ",
                ),
                self._document(
                    203,
                    document_origin=1,
                    document_kind=1,
                    operation_user_id=30,
                    signer="ANA PEREZ",
                ),
                self._document(
                    204,
                    document_origin=1,
                    document_kind=1,
                    document_user_id=40,
                    signer="LUIS ROJAS",
                ),
                self._document(205, document_origin=2),
                self._document(206, document_origin=3),
            ],
            period=2026,
            scope="oficina",
            depe_id=10,
        )

        reports = export_report_files(
            self.db_path,
            self.root,
            period=2026,
            scope="oficina",
            depe_id=10,
            separate_personal=True,
        )

        office_file = report_path(self.root, period=2026, scope="oficina", depe_id=10)
        manual_file = manual_report_path(
            self.root,
            period=2026,
            scope="oficina",
            depe_id=10,
        )
        ana_file = personal_report_path(
            self.root,
            period=2026,
            scope="oficina",
            depe_id=10,
            user_id="30",
            signer="ANA PEREZ",
        )
        luis_file = personal_report_path(
            self.root,
            period=2026,
            scope="oficina",
            depe_id=10,
            user_id="40",
            signer="LUIS ROJAS",
        )
        self.assertEqual(
            reports,
            [(office_file, 2), (manual_file, 2), (ana_file, 2), (luis_file, 1)],
        )
        with zipfile.ZipFile(office_file) as workbook:
            office_sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        with zipfile.ZipFile(manual_file) as workbook:
            manual_sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        with zipfile.ZipFile(ana_file) as workbook:
            ana_sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        with zipfile.ZipFile(luis_file) as workbook:
            luis_sheet = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
        self.assertIn("ASUNTO 201", office_sheet)
        self.assertIn("ASUNTO 212", office_sheet)
        self.assertNotIn("ASUNTO 202", office_sheet)
        self.assertIn("ASUNTO 205", manual_sheet)
        self.assertIn("ASUNTO 206", manual_sheet)
        self.assertIn("ASUNTO 202", ana_sheet)
        self.assertIn("ASUNTO 203", ana_sheet)
        self.assertNotIn("ASUNTO 204", ana_sheet)
        self.assertIn("ASUNTO 204", luis_sheet)
        self.assertNotIn("ASUNTO 202", luis_sheet)

    def test_include_personal_is_propagated_to_batch_and_file_download(self) -> None:
        client = SgdApiClient("https://sgd.example/")
        with patch.object(client, "_request", return_value={}) as request:
            client.related_documents_batch(
                [1],
                scope="oficina",
                depe_id=10,
                include_personal=True,
            )
        self.assertEqual(request.call_args.kwargs["json"]["include_personal"], 1)

        response = Mock(status_code=200)
        response.iter_content.return_value = []
        destination = self.root / "archivo.pdf"
        with patch.object(client, "_send_with_retries", return_value=response) as send:
            client.download_file(
                50,
                destination,
                scope="oficina",
                depe_id=10,
                include_personal=True,
            )
        self.assertEqual(send.call_args.kwargs["params"]["include_personal"], 1)

    def test_separate_export_reports_each_invalid_classification_cause(self) -> None:
        upsert_documents(
            self.db_path,
            [
                self._document(207, document_kind=0),
                self._document(208, document_origin=1),
                self._document(209, document_origin=1, document_kind=7),
                self._document(210, document_origin=1, document_kind=1),
                self._document(
                    211,
                    document_origin=1,
                    document_kind=1,
                    operation_user_id="NO NUMERICO",
                ),
            ],
            period=2026,
            scope="oficina",
            depe_id=10,
        )
        with self.assertRaises(ValueError) as raised:
            export_report_files(
                self.db_path,
                self.root,
                period=2026,
                scope="oficina",
                depe_id=10,
                separate_personal=True,
            )
        message = str(raised.exception)
        self.assertIn("5 documento(s)", message)
        self.assertIn("docu_origen ausente o vacío: 1. Reg. SGD: 207.", message)
        self.assertIn("docu_tipo ausente", message)
        self.assertIn("docu_tipo no reconocido (7)", message)
        self.assertIn("docu_idusuario y oper_idusuario ausentes o vacíos", message)
        self.assertIn("Reg. SGD: 210.", message)
        self.assertIn("oper_idusuario no es numérico", message)
        self.assertIn("Reg. SGD: 211.", message)
        self.assertIn("app.log", message)

    def test_schema_migration_backfills_report_fields_from_raw_json(self) -> None:
        self._create_version_3_database()

        init_database(self.db_path)

        with closing(sqlite3.connect(self.db_path)) as connection:
            row = connection.execute(
                """
                SELECT recipient_offices, project_cui, procedure_type_id,
                       procedure_type_description, document_acronyms
                FROM documents WHERE iddocumento = 1
                """
            ).fetchone()
            version = connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
        self.assertEqual(
            row,
            ("OFICINA DE TESORERIA", "2468101", 4, "EJECUCION DE OBRA", "GRH/GGR"),
        )
        self.assertEqual(version, (str(SCHEMA_VERSION),))

    @staticmethod
    def _document(
        document_id: int,
        offices: object = ...,
        *,
        cui: object = ...,
        procedure_type_id: object = ...,
        procedure_type: object = ...,
        number: object = ...,
        document_type: str = "OFICIO",
        document_date: object = ...,
        acronyms: object = ...,
        document_origin: object = ...,
        document_kind: object = ...,
        document_user_id: object = ...,
        operation_user_id: object = ...,
        signer: object = ...,
    ) -> dict[str, object]:
        document: dict[str, object] = {
            "iddocumento": document_id,
            "iddocumento_text": str(document_id).zfill(8),
            "tdoc_descripcion": document_type,
            "docu_asunto": f"ASUNTO {document_id}",
            "files": [],
        }
        document["docu_numero_doc"] = document_id if number is ... else number
        if offices is not ...:
            document["oficinas_destinatarias"] = offices
        if cui is not ...:
            document["cui_proyecto"] = cui
        if procedure_type_id is not ...:
            document["tipo_tramite"] = procedure_type_id
        if procedure_type is not ...:
            document["tipo_tramite_descripcion"] = procedure_type
        if document_date is not ...:
            document["docu_fecha_doc"] = document_date
        if acronyms is not ...:
            document["docu_siglas_doc"] = acronyms
        if document_origin is not ...:
            document["docu_origen"] = document_origin
        if document_kind is not ...:
            document["docu_tipo"] = document_kind
        if document_user_id is not ...:
            document["docu_idusuario"] = document_user_id
        if operation_user_id is not ...:
            document["oper_idusuario"] = operation_user_id
        if signer is not ...:
            document["docu_firma"] = signer
        return document

    def _create_version_3_database(self) -> None:
        raw_json = json.dumps(
            self._document(
                1,
                "OFICINA DE TESORERIA",
                cui=2468101,
                procedure_type_id=4,
                procedure_type="EJECUCION DE OBRA",
                document_date="2026-10-20",
                acronyms="GRH/GGR",
            )
        )
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.executescript(
                """
                CREATE TABLE documents (
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
                );
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                INSERT INTO metadata (key, value) VALUES ('schema_version', '3');
                """
            )
            connection.execute(
                """
                INSERT INTO documents (
                    iddocumento, period, scope, depe_id, relation_kind,
                    document_type, storage_type, raw_json
                ) VALUES (1, 2026, 'oficina', 10, 'principal', 'OFICIO', 'Fisico', ?)
                """,
                (raw_json,),
            )
            connection.commit()


if __name__ == "__main__":
    unittest.main()
