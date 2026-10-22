from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path

from cargos_downloader.excel_exporter import (
    export_report,
    preview_sheets,
    related_preview_rows,
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
            self.assertEqual(row[1], row[-1])

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
            ],
        )
        self.assertEqual(rows[1][-3:], ["2468101", "EJECUCION DE OBRA", "000001"])
        for row in rows[2:]:
            self.assertEqual(row[-3:-1], ["", ""])
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
        self.assertIn('mergeCell ref="N1"', sheet)
        self.assertIn('mergeCell ref="N3"', sheet)

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
        self.assertEqual(main_rows[1][-1], "000635")
        self.assertEqual(related_rows[1][1], "INFORME 000027-2026-GRH/ORA")
        self.assertEqual(related_rows[1][-1], "000027")

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
