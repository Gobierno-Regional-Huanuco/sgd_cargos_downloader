from __future__ import annotations

import re
import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path

from cargos_downloader.downloader import DownloadOptions, _file_tasks, run_file_download
from cargos_downloader.excel_exporter import (
    classification_warning_message,
    export_report,
    preview_sheets,
    report_path,
)
from cargos_downloader.storage import (
    database_path,
    file_catalog_path,
    file_download_sources,
    mark_file_download,
    registrant_names,
    upsert_documents,
    upsert_file_download_tasks,
    upsert_related_records,
)

PERIOD = 2026
SCOPE = "oficina"
DEPE_ID = 10


def document(
    document_id: int,
    *,
    origin: object = ...,
    kind: object = ...,
    user_id: object = ...,
    operation_user_id: object = ...,
    signer: object = ...,
    document_type: str = "OFICIO",
    number: object = ...,
    acronyms: object = ...,
    files: int = 0,
) -> dict[str, object]:
    data: dict[str, object] = {
        "iddocumento": document_id,
        "tdoc_descripcion": document_type,
        "docu_asunto": f"ASUNTO {document_id}",
        "docu_fecha_doc": "2026-03-10",
        "docu_numero_doc": document_id if number is ... else number,
        "files": [
            {
                "id": document_id * 10 + index,
                "file_name": f"adjunto{index}.pdf",
                "file_tipo": "application/pdf",
                "file_size": 5,
            }
            for index in range(files)
        ],
    }
    optional = {
        "docu_origen": origin,
        "docu_tipo": kind,
        "docu_idusuario": user_id,
        "oper_idusuario": operation_user_id,
        "docu_firma": signer,
        "docu_siglas_doc": acronyms,
    }
    data.update({key: value for key, value in optional.items() if value is not ...})
    return data


def sheet_texts(workbook_path: Path) -> list[tuple[str, str]]:
    with zipfile.ZipFile(workbook_path) as workbook:
        names = re.findall(r'<sheet name="([^"]+)"', workbook.read("xl/workbook.xml").decode("utf-8"))
        return [
            (name, workbook.read(f"xl/worksheets/sheet{index}.xml").decode("utf-8"))
            for index, name in enumerate(names, start=1)
        ]


class SingleWorkbookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.db_path = database_path(self.root)
        upsert_documents(
            self.db_path,
            [
                document(201, origin=1, kind=0, user_id=12),
                document(212, origin=1, kind=None, user_id=12),
                document(202, origin=1, kind=1, user_id=30, operation_user_id=999, signer="ANA PEREZ"),
                document(203, origin=1, kind=1, operation_user_id=30, signer="ANA PEREZ"),
                document(204, origin=1, kind=1, user_id=40, signer="LUIS ROJAS"),
                document(205, origin=2, user_id=30, signer="DIRECTOR MINSA", document_type="CARTA"),
                document(206, origin=3, user_id=40, signer="FIRMA PIDE"),
                document(207, origin=2, user_id=99),
                document(208, kind=0),
            ],
            period=PERIOD,
            scope=SCOPE,
            depe_id=DEPE_ID,
        )

    def test_exports_one_workbook_with_origin_registrant_and_external_sheet(self) -> None:
        output = report_path(self.root, period=PERIOD, scope=SCOPE, depe_id=DEPE_ID)

        result = export_report(self.db_path, output, period=PERIOD, scope=SCOPE, depe_id=DEPE_ID)

        self.assertEqual(result.records, 9)
        self.assertEqual(result.external_records, 3)
        self.assertEqual(result.unclassified, {"docu_origen ausente o vacío": [208]})
        self.assertEqual(sorted(path.name for path in self.root.glob("*.xlsx")), [output.name])

        sheets = sheet_texts(output)
        self.assertEqual([name for name, _ in sheets], ["2026 OFICIO", "2026 EXTERNOS"])
        office_sheet, external_sheet = sheets[0][1], sheets[1][1]

        for document_id in (201, 212, 202, 203, 204, 208):
            self.assertIn(f"ASUNTO {document_id}<", office_sheet)
        for document_id in (205, 206, 207):
            self.assertNotIn(f"ASUNTO {document_id}<", office_sheet)
            self.assertIn(f"ASUNTO {document_id}<", external_sheet)

        self.assertIn("<t>Oficina</t>", office_sheet)
        self.assertIn("<t>Personal</t>", office_sheet)
        self.assertIn("<t>Sin clasificar</t>", office_sheet)
        self.assertIn("<t>30 - ANA PEREZ</t>", office_sheet)
        self.assertIn("<t>12</t>", office_sheet)

        self.assertIn("REGISTRO DE DOCUMENTOS EXTERNOS", external_sheet)
        self.assertIn('<c r="A4" s="2" t="inlineStr"><is><t>Tipo</t>', external_sheet)
        self.assertIn("<t>CARTA</t>", external_sheet)
        self.assertIn("<t>Manual/Externo</t>", external_sheet)
        self.assertIn("<t>Interoperabilidad/PIDE</t>", external_sheet)
        self.assertIn("<t>30 - ANA PEREZ</t>", external_sheet)
        self.assertIn("<t>40 - LUIS ROJAS</t>", external_sheet)
        self.assertIn("<t>99</t>", external_sheet)

    def test_sheets_have_filter_frozen_header_and_full_width_title(self) -> None:
        output = report_path(self.root, period=PERIOD, scope=SCOPE, depe_id=DEPE_ID)
        export_report(self.db_path, output, period=PERIOD, scope=SCOPE, depe_id=DEPE_ID)

        sheets = dict(sheet_texts(output))
        self.assertIn('<autoFilter ref="A4:Q10"/>', sheets["2026 OFICIO"])
        self.assertIn('<autoFilter ref="A4:R7"/>', sheets["2026 EXTERNOS"])
        self.assertIn('mergeCell ref="A1:R1"', sheets["2026 EXTERNOS"])
        self.assertIn('state="frozen"', sheets["2026 OFICIO"])
        with zipfile.ZipFile(output) as workbook:
            workbook_xml = workbook.read("xl/workbook.xml").decode("utf-8")
        self.assertIn("'2026 EXTERNOS'!$A$4:$R$7", workbook_xml)

    def test_unclassified_warning_lists_cause_and_ids(self) -> None:
        message = classification_warning_message({"docu_origen ausente o vacío": [208]})
        self.assertIn("1 documento(s)", message)
        self.assertIn("Sin clasificar", message)
        self.assertIn("docu_origen ausente o vacío: 1. Reg. SGD: 208.", message)
        self.assertIn("app.log", message)

    def test_preview_matches_workbook_sheets(self) -> None:
        sheets = preview_sheets(self.db_path, period=PERIOD, scope=SCOPE, depe_id=DEPE_ID)

        self.assertEqual([(name, total) for name, total, _ in sheets], [("2026 OFICIO", 6), ("2026 EXTERNOS", 3)])
        external_rows = sheets[1][2]
        self.assertEqual(external_rows[0][:2], ["ID", "Tipo"])
        self.assertEqual(external_rows[0][-3:], ["Origen", "Registrado por", "Reg. SGD"])
        self.assertEqual(
            {row[-1]: row[-2] for row in external_rows[1:]},
            {205: "30 - ANA PEREZ", 206: "40 - LUIS ROJAS", 207: "99"},
        )

    def test_registrant_names_come_from_personal_signers(self) -> None:
        names = registrant_names(self.db_path, period=PERIOD, scope=SCOPE, depe_id=DEPE_ID)
        self.assertEqual(names, {"30": "ANA PEREZ", "40": "LUIS ROJAS"})



class RegistrantNameTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = database_path(Path(self.temp_dir.name))

    def _names(self, documents: list[dict[str, object]]) -> dict[str, str]:
        upsert_documents(self.db_path, documents, period=PERIOD, scope=SCOPE, depe_id=DEPE_ID)
        return registrant_names(self.db_path, period=PERIOD, scope=SCOPE, depe_id=DEPE_ID)

    def test_signer_shared_by_two_users_leaves_both_without_name(self) -> None:
        names = self._names(
            [
                document(1, origin=1, kind=1, user_id=6138, signer="ALEX CRUZ"),
                document(2, origin=1, kind=1, user_id=6138, signer="ALEX CRUZ"),
                document(3, origin=1, kind=1, user_id=5755, signer="ALEX CRUZ"),
                document(4, origin=1, kind=1, user_id=4, signer="WALTHER AGUIRRE"),
            ]
        )
        self.assertEqual(names, {"4": "WALTHER AGUIRRE"})

    def test_user_with_two_signers_has_no_name(self) -> None:
        names = self._names(
            [
                document(1, origin=1, kind=1, user_id=30, signer="ANA PEREZ"),
                document(2, origin=1, kind=1, user_id=30, signer="LUIS ROJAS"),
            ]
        )
        self.assertEqual(names, {})

    def test_signer_spelling_differences_are_the_same_person(self) -> None:
        names = self._names(
            [
                document(1, origin=1, kind=1, user_id=30, signer="ANA  PEREZ"),
                document(2, origin=1, kind=1, user_id=30, signer="Ana Perez"),
                document(3, origin=1, kind=1, user_id=30, signer="ANA PEREZ"),
            ]
        )
        self.assertEqual(names, {"30": "ANA PEREZ"})

    def test_names_never_come_from_office_or_external_signers(self) -> None:
        names = self._names(
            [
                document(1, origin=1, kind=0, user_id=12, signer="JEFE OFICINA"),
                document(2, origin=2, user_id=40, signer="DIRECTOR MINSA"),
            ]
        )
        self.assertEqual(names, {})

class FileLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.db_path = database_path(self.root)
        upsert_documents(
            self.db_path,
            [
                document(1, origin=1, kind=0, user_id=12, number=123, acronyms="GRH/GRI", files=1),
                document(2, origin=1, kind=1, user_id=30, signer="ANA PEREZ", number=8, acronyms="GRH", files=1),
                document(3, origin=2, user_id=30, number=123, files=1),
                document(4, origin=3, number=45, acronyms="PCM/SGTD", files=1),
                document(5, origin=2, user_id=40, document_type="CARTA", number="S/N", files=1),
            ],
            period=PERIOD,
            scope=SCOPE,
            depe_id=DEPE_ID,
        )
        upsert_related_records(
            self.db_path,
            [(document(6, origin=1, kind=0, document_type="INFORME", number=9, acronyms="GRH", files=1), 3)],
            period=PERIOD,
            scope=SCOPE,
            depe_id=DEPE_ID,
        )

    def _tasks(self) -> dict[int, str]:
        sources = file_download_sources(self.db_path, period=PERIOD, scope=SCOPE, depe_id=DEPE_ID)
        names = registrant_names(self.db_path, period=PERIOD, scope=SCOPE, depe_id=DEPE_ID)
        tasks = _file_tasks(self.root, sources, 1000, names)
        return {task["document_id"]: Path(task["relative_path"]).as_posix() for task in tasks}

    def test_files_are_grouped_by_origin_and_registrant(self) -> None:
        self.assertEqual(
            self._tasks(),
            {
                1: "OFICIO/000001-001000/OFICIO 000123 GRH_GRI/adjunto0.pdf",
                2: "_PERSONALES/30 - ANA PEREZ/OFICIO/000001-001000/OFICIO 000008 GRH/adjunto0.pdf",
                3: "_EXTERNOS/30 - ANA PEREZ/OFICIO/000001-001000/OFICIO 000123 [Reg 3]/adjunto0.pdf",
                4: "_EXTERNOS/SIN USUARIO/OFICIO/000001-001000/OFICIO 000045 PCM_SGTD/adjunto0.pdf",
                5: "_EXTERNOS/40/CARTA/SIN NUMERO/CARTA S_N [Reg 5]/adjunto0.pdf",
                6: (
                    "_EXTERNOS/30 - ANA PEREZ/OFICIO/000001-001000/OFICIO 000123 [Reg 3]/"
                    "INFORME 000009 GRH_adjunto0.pdf"
                ),
            },
        )

    def test_already_downloaded_file_is_moved_without_downloading_again(self) -> None:
        legacy = Path("OFICIO") / "000001-001000" / "OFICIO 000123" / "adjunto0.pdf"
        (self.root / legacy).parent.mkdir(parents=True)
        (self.root / legacy).write_bytes(b"12345")
        upsert_file_download_tasks(
            self.root,
            [
                {
                    "relative_path": str(legacy),
                    "file_id": 30,
                    "document_id": 3,
                    "master_id": None,
                    "file_name": "adjunto0.pdf",
                    "mime_type": "application/pdf",
                    "expected_size": 5,
                }
            ],
        )
        mark_file_download(self.root, str(legacy), status="descargado", attempted=True)
        options = DownloadOptions(
            service_url="https://sgd.invalid/",
            token="token",
            output_dir=self.root,
            scope=SCOPE,
            depe_id=DEPE_ID,
            period=PERIOD,
            per_page=10,
            group_size=1000,
            include_related=True,
            include_personal_for_office=True,
        )
        messages: list[str] = []

        stats = run_file_download(options, log=messages.append, stopped=lambda: True)

        new_path = Path(self._tasks()[3])
        self.assertEqual(stats.files_moved, 1)
        self.assertFalse((self.root / legacy).exists())
        self.assertFalse((self.root / "OFICIO" / "000001-001000" / "OFICIO 000123").exists())
        self.assertEqual((self.root / new_path).read_bytes(), b"12345")
        with closing(sqlite3.connect(file_catalog_path(self.root))) as connection:
            rows = dict(
                connection.execute(
                    "SELECT relative_path, status FROM file_downloads WHERE file_id = 30"
                ).fetchall()
            )
        self.assertEqual({Path(path).as_posix(): status for path, status in rows.items()}, {new_path.as_posix(): "descargado"})
        self.assertTrue(any("reubicados" in message for message in messages))


if __name__ == "__main__":
    unittest.main()
