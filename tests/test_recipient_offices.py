from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path

from cargos_downloader.excel_exporter import export_report, preview_sheets
from cargos_downloader.storage import SCHEMA_VERSION, init_database, upsert_documents


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
        self.assertIn('min="5" max="5" width="48"', sheet)
        self.assertIn('wrapText="1"', styles)

    def test_cui_and_procedure_type_are_the_last_report_columns(self) -> None:
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
            ],
        )
        self.assertEqual(rows[1][-2:], ["2468101", "EJECUCION DE OBRA"])
        for row in rows[2:]:
            self.assertEqual(row[-2:], ["", ""])
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
        self.assertIn('mergeCell ref="M1"', sheet)
        self.assertIn('mergeCell ref="M3"', sheet)

    def test_schema_migration_backfills_report_fields_from_raw_json(self) -> None:
        self._create_version_3_database()

        init_database(self.db_path)

        with closing(sqlite3.connect(self.db_path)) as connection:
            row = connection.execute(
                """
                SELECT recipient_offices, project_cui, procedure_type_id,
                       procedure_type_description
                FROM documents WHERE iddocumento = 1
                """
            ).fetchone()
            version = connection.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
        self.assertEqual(row, ("OFICINA DE TESORERIA", "2468101", 4, "EJECUCION DE OBRA"))
        self.assertEqual(version, (str(SCHEMA_VERSION),))

    @staticmethod
    def _document(
        document_id: int,
        offices: object = ...,
        *,
        cui: object = ...,
        procedure_type_id: object = ...,
        procedure_type: object = ...,
    ) -> dict[str, object]:
        document: dict[str, object] = {
            "iddocumento": document_id,
            "iddocumento_text": str(document_id).zfill(8),
            "tdoc_descripcion": "OFICIO",
            "docu_asunto": f"ASUNTO {document_id}",
            "files": [],
        }
        if offices is not ...:
            document["oficinas_destinatarias"] = offices
        if cui is not ...:
            document["cui_proyecto"] = cui
        if procedure_type_id is not ...:
            document["tipo_tramite"] = procedure_type_id
        if procedure_type is not ...:
            document["tipo_tramite_descripcion"] = procedure_type
        return document

    def _create_version_3_database(self) -> None:
        raw_json = json.dumps(
            self._document(
                1,
                "OFICINA DE TESORERIA",
                cui=2468101,
                procedure_type_id=4,
                procedure_type="EJECUCION DE OBRA",
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
