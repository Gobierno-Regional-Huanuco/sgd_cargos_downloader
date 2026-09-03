from __future__ import annotations

import sys
from datetime import date
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QHeaderView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from cargos_downloader.api import SgdApiClient, SgdApiError
from cargos_downloader.config import APP_DIR, AppConfig, load_config, save_config
from cargos_downloader.downloader import DownloadOptions, run_download, run_file_download
from cargos_downloader.excel_exporter import (
    export_report,
    preview_sheets,
    related_count,
    related_preview_rows,
    report_path,
)
from cargos_downloader.storage import (
    clear_database,
    clear_user_databases,
    database_has_documents,
    database_path,
    scoped_output_dir,
    user_has_local_data,
)


PREVIEW_ROW_LIMIT = 300
RELATED_ROW_LIMIT = 500
LOG_FILE = APP_DIR / "app.log"
PROGRESS_STYLE_RUNNING = """
QProgressBar::chunk {
    background-color: #0b8fe8;
}
"""
PROGRESS_STYLE_DONE = """
QProgressBar::chunk {
    background-color: #1f9d55;
}
"""
PROGRESS_STYLE_ERROR = """
QProgressBar::chunk {
    background-color: #c0392b;
}
"""


class DownloadThread(QThread):
    log_message = Signal(str)
    progress_changed = Signal(int, int, str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, options: DownloadOptions):
        super().__init__()
        self.options = options
        self._stop_requested = False

    def stop(self) -> None:
        self._stop_requested = True

    def run(self) -> None:
        try:
            stats = run_download(
                self.options,
                log=self.log_message.emit,
                stopped=lambda: self._stop_requested,
                progress=self.progress_changed.emit,
            )
            self.completed.emit(stats)
        except Exception as exc:
            self.failed.emit(str(exc))


class FileDownloadThread(QThread):
    log_message = Signal(str)
    progress_changed = Signal(int, int, str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, options: DownloadOptions):
        super().__init__()
        self.options = options
        self._stop_requested = False

    def stop(self) -> None:
        self._stop_requested = True

    def run(self) -> None:
        try:
            stats = run_file_download(
                self.options,
                log=self.log_message.emit,
                stopped=lambda: self._stop_requested,
                progress=self.progress_changed.emit,
            )
            self.completed.emit(stats)
        except Exception as exc:
            self.failed.emit(str(exc))


class PreviewThread(QThread):
    loaded = Signal(int, object)
    failed = Signal(int, str)

    def __init__(self, request_id: int, db_path: Path, period: int, scope: str, depe_id: int):
        super().__init__()
        self.request_id = request_id
        self.db_path = db_path
        self.period = period
        self.scope = scope
        self.depe_id = depe_id

    def run(self) -> None:
        try:
            sheets = preview_sheets(
                self.db_path,
                period=self.period,
                scope=self.scope,
                depe_id=self.depe_id,
                limit_per_sheet=PREVIEW_ROW_LIMIT,
            )
            self.loaded.emit(self.request_id, sheets)
        except Exception as exc:
            self.failed.emit(self.request_id, str(exc))


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuracion")
        self.resize(560, 235)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.service_url = QLineEdit(config.service_url)
        self.include_related = QCheckBox("Incluir documentos relacionados")
        self.include_related.setChecked(config.include_related)
        self.include_personal_for_office = QCheckBox("En oficina, incluir documentos personales")
        self.include_personal_for_office.setChecked(config.include_personal_for_office)
        self.output_dir = QLineEdit(config.output_dir)
        self.output_button = QPushButton("Seleccionar")
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_dir)
        output_layout.addWidget(self.output_button)

        self.group_size = QSpinBox()
        self.group_size.setRange(100, 10000)
        self.group_size.setSingleStep(100)
        self.group_size.setValue(config.group_size)

        self.per_page = QSpinBox()
        self.per_page.setRange(50, 1000)
        self.per_page.setSingleStep(50)
        self.per_page.setValue(max(500, config.per_page))

        self.related_batch_size = QSpinBox()
        self.related_batch_size.setRange(50, 1000)
        self.related_batch_size.setSingleStep(50)
        self.related_batch_size.setValue(config.related_batch_size)

        form.addRow("URL SGD", self.service_url)
        form.addRow("", self.include_related)
        form.addRow("", self.include_personal_for_office)
        form.addRow("Destino raiz", output_layout)
        form.addRow("Grupo", self.group_size)
        form.addRow("Pagina", self.per_page)
        form.addRow("Lote relacionados", self.related_batch_size)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)

        self.output_button.clicked.connect(self.pick_output_dir)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def pick_output_dir(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Carpeta destino", self.output_dir.text())
        if selected:
            self.output_dir.setText(selected)

    def config_values(self, base: AppConfig) -> AppConfig:
        return AppConfig(
            service_url=self.service_url.text().strip(),
            output_dir=self.output_dir.text().strip(),
            last_username=base.last_username,
            period=base.period,
            group_size=self.group_size.value(),
            per_page=self.per_page.value(),
            include_related=self.include_related.isChecked(),
            include_personal_for_office=self.include_personal_for_office.isChecked(),
            related_batch_size=self.related_batch_size.value(),
        )


class RelatedDialog(QDialog):
    def __init__(self, title: str, rows: list[list[object]], parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(900, 420)

        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._load_rows(rows)

    def _load_rows(self, rows: list[list[object]]) -> None:
        if not rows:
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return
        headers = [str(value) for value in rows[0]]
        data_rows = rows[1:]
        self.table.setColumnCount(len(headers))
        self.table.setRowCount(len(data_rows))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setUpdatesEnabled(False)
        try:
            for row_index, row in enumerate(data_rows):
                for col_index, value in enumerate(row):
                    self.table.setItem(row_index, col_index, QTableWidgetItem(str(value or "")))
            self.table.resizeColumnsToContents()
        finally:
            self.table.setUpdatesEnabled(True)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.client: SgdApiClient | None = None
        self.token: str | None = None
        self.user: dict | None = None
        self.worker: QThread | None = None
        self.preview_workers: list[PreviewThread] = []
        self.preview_request_id = 0
        self.preview_sheets_data: list[tuple[str, int, list[list[object]]]] = []

        self.setWindowTitle("SGD Cargos Downloader")
        self.resize(900, 680)
        self._build_ui()
        self._load_config_values()
        self._set_logged_out()

    def _build_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        login_box = QGroupBox("Acceso")
        login_grid = QGridLayout(login_box)
        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.login_button = QPushButton("Iniciar sesión")
        self.logout_button = QPushButton("Cerrar sesión")
        self.change_user_button = QPushButton("Cambiar usuario")
        self.settings_button = QPushButton("Configuracion")
        self.user_label = QLabel("Sin sesión")
        self.user_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        login_grid.addWidget(QLabel("Usuario"), 0, 0)
        login_grid.addWidget(self.username, 0, 1)
        login_grid.addWidget(QLabel("Clave"), 1, 0)
        login_grid.addWidget(self.password, 1, 1)
        login_grid.addWidget(self.login_button, 0, 2)
        login_grid.addWidget(self.logout_button, 1, 2)
        login_grid.addWidget(self.change_user_button, 0, 3)
        login_grid.addWidget(self.settings_button, 1, 3)
        login_grid.addWidget(self.user_label, 2, 0, 1, 4)
        layout.addWidget(login_box)

        filters_box = QGroupBox("Descarga")
        filters_grid = QGridLayout(filters_box)
        self.office_combo = QComboBox()
        self.scope_combo = QComboBox()
        self.period_combo = QComboBox()
        self.start_button = QPushButton("Descargar registros")
        self.files_button = QPushButton("Descargar archivos")
        self.export_button = QPushButton("Exportar Excel")
        self.clear_db_button = QPushButton("Limpiar base")
        self.cancel_button = QPushButton("Cancelar")

        action_buttons = QHBoxLayout()
        action_buttons.setContentsMargins(0, 0, 0, 0)
        action_buttons.setSpacing(8)
        for button in (
            self.clear_db_button,
            self.export_button,
            self.files_button,
            self.start_button,
            self.cancel_button,
        ):
            button.setMinimumHeight(30)
            action_buttons.addWidget(button)

        filters_grid.addWidget(QLabel("Oficina"), 0, 0)
        filters_grid.addWidget(self.office_combo, 0, 1, 1, 4)
        filters_grid.addWidget(QLabel("Alcance"), 1, 0)
        filters_grid.addWidget(self.scope_combo, 1, 1)
        filters_grid.addWidget(QLabel("Periodo"), 1, 2)
        filters_grid.addWidget(self.period_combo, 1, 3)
        filters_grid.addLayout(action_buttons, 2, 0, 1, 5)
        layout.addWidget(filters_box)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setFormat("0%")
        layout.addWidget(self.progress)

        self.log_toggle = QToolButton()
        self.log_toggle.setText("Detalle de acciones")
        self.log_toggle.setCheckable(True)
        self.log_toggle.setChecked(False)
        self.log_toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.log_toggle.setArrowType(Qt.RightArrow)
        layout.addWidget(self.log_toggle)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setVisible(False)
        layout.addWidget(self.log)

        preview_box = QGroupBox("Vista previa")
        preview_layout = QVBoxLayout(preview_box)
        preview_header = QHBoxLayout()
        preview_header.addWidget(QLabel("Hoja"))
        self.sheet_combo = QComboBox()
        preview_header.addWidget(self.sheet_combo, stretch=1)
        self.related_button = QPushButton("Ver relacionados")
        self.related_button.setEnabled(False)
        preview_header.addWidget(self.related_button)
        preview_layout.addLayout(preview_header)
        self.preview_status = QLabel("")
        preview_layout.addWidget(self.preview_status)
        self.preview_table = QTableWidget()
        self.preview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.preview_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        preview_layout.addWidget(self.preview_table)
        layout.addWidget(preview_box, stretch=1)

        self.setCentralWidget(root)

        self.login_button.clicked.connect(self.login)
        self.logout_button.clicked.connect(self.logout)
        self.change_user_button.clicked.connect(self.change_user)
        self.username.editingFinished.connect(self._sync_user_lock)
        self.settings_button.clicked.connect(self.open_settings)
        self.start_button.clicked.connect(self.start_download)
        self.files_button.clicked.connect(self.start_file_download)
        self.export_button.clicked.connect(self.export_excel)
        self.clear_db_button.clicked.connect(self.clear_local_database)
        self.cancel_button.clicked.connect(self.cancel_download)
        self.scope_combo.currentIndexChanged.connect(self.load_preview)
        self.office_combo.currentIndexChanged.connect(self.load_preview)
        self.period_combo.currentIndexChanged.connect(self.load_preview)
        self.log_toggle.toggled.connect(self._toggle_log)
        self.sheet_combo.currentIndexChanged.connect(self._show_preview_sheet)
        self.related_button.clicked.connect(self.open_related_documents)
        self.preview_table.cellDoubleClicked.connect(lambda _row, _column: self.open_related_documents())

    def _load_config_values(self) -> None:
        self.username.setText(self.config.last_username)
        self.period_combo.clear()
        for year in range(2023, date.today().year + 1):
            self.period_combo.addItem(str(year), year)
        period_index = self.period_combo.findData(self.config.period)
        self.period_combo.setCurrentIndex(max(0, period_index))

    def _read_config_values(self) -> AppConfig:
        return AppConfig(
            service_url=self.config.service_url,
            output_dir=self.config.output_dir,
            last_username=self.username.text().strip(),
            period=int(self.period_combo.currentData() or 2023),
            group_size=self.config.group_size,
            per_page=self.config.per_page,
            include_related=self.config.include_related,
            include_personal_for_office=self.config.include_personal_for_office,
            related_batch_size=self.config.related_batch_size,
        )

    def _set_logged_out(self) -> None:
        self.client = None
        self.token = None
        self.user = None
        self.user_label.setText("Sin sesión")
        self.office_combo.clear()
        self.scope_combo.clear()
        self.scope_combo.addItem("Personal", "personal")
        self.logout_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.files_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self._sync_user_lock()
        self._clear_preview()
        self._update_action_buttons()

    def _set_logged_in(self, payload: dict) -> None:
        self.user = payload.get("user", {})
        self.user_label.setText(
            f"{self.user.get('adm_name', '')} {self.user.get('adm_lastname', '')} - "
            f"{self.user.get('adm_email', '')}"
        )

        self.office_combo.clear()
        for office in self.user.get("offices", []):
            label = f"{office.get('depe_nombre')} ({office.get('depe_id')})"
            self.office_combo.addItem(label, office)

        self.scope_combo.clear()
        self.scope_combo.addItem("Personal", "personal")
        if self.user.get("can_download_office"):
            self.scope_combo.addItem("Oficina", "oficina")

        self.logout_button.setEnabled(True)
        self.start_button.setEnabled(True)
        self.change_user_button.setEnabled(False)
        self.username.setEnabled(False)
        self._update_action_buttons()
        self.load_preview()

    def open_settings(self) -> None:
        base = self._read_config_values()
        dialog = SettingsDialog(base, self)
        if dialog.exec() != QDialog.Accepted:
            return
        updated = dialog.config_values(base)
        service_url_changed = updated.service_url != self.config.service_url
        self.config = updated
        save_config(self.config)
        if service_url_changed and self.token:
            self._close_session_after_service_change()
            self._append_log("URL SGD actualizada. Sesion cerrada; debe iniciar sesion nuevamente.")
            return
        if not self.token:
            self._sync_user_lock()
        self._append_log("Configuracion actualizada.")
        self.load_preview()

    def _close_session_after_service_change(self) -> None:
        if self.client:
            self.client.logout()
        self.client = None
        self.token = None
        self.user = None
        self.office_combo.clear()
        self.scope_combo.clear()
        self.scope_combo.addItem("Personal", "personal")
        self.logout_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.files_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.username.setEnabled(not user_has_local_data(self._output_root(), self._active_username()))
        self.change_user_button.setEnabled(not self.username.isEnabled())
        self._clear_preview()
        self._update_action_buttons()

    def _output_root(self) -> Path:
        return Path(self.config.output_dir).expanduser()

    def _active_username(self) -> str:
        return self.username.text().strip()

    def _active_output_dir(self, scope: str | None = None) -> Path:
        selected_scope = scope or str(self.scope_combo.currentData() or "personal")
        period = int(self.period_combo.currentData() or self.config.period or 2023)
        return scoped_output_dir(self._output_root(), self._active_username(), period, selected_scope)

    def _is_downloading(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    def _active_database_has_data(self) -> bool:
        if not self._active_username():
            return False
        return database_has_documents(self._active_output_dir())

    def _preview_has_records(self) -> bool:
        return any(total > 0 for _name, total, _rows in self.preview_sheets_data)

    def _update_action_buttons(self) -> None:
        downloading = self._is_downloading()
        logged_in = self.token is not None
        has_office = self.office_combo.currentData() is not None
        has_data = self._active_database_has_data()
        self.start_button.setEnabled(logged_in and has_office and not downloading)
        self.export_button.setEnabled(logged_in and has_office and has_data and self._preview_has_records() and not downloading)
        self.files_button.setEnabled(logged_in and has_office and has_data and not downloading)
        self.clear_db_button.setEnabled(logged_in and has_office and has_data and not downloading)
        self.cancel_button.setEnabled(downloading)

    def _sync_user_lock(self) -> None:
        has_data = user_has_local_data(self._output_root(), self._active_username())
        self.username.setEnabled(not has_data)
        self.change_user_button.setEnabled(has_data)
        if has_data:
            self.user_label.setText("Base local encontrada. Ingrese solo la clave para iniciar sesion.")
        else:
            self.user_label.setText("Sin sesion")
        self._update_action_buttons()

    def change_user(self) -> None:
        username = self._active_username()
        if not username:
            self.username.setEnabled(True)
            self.change_user_button.setEnabled(False)
            return

        answer = QMessageBox.question(
            self,
            "Cambiar usuario",
            "Cambiar de usuario eliminara las bases locales del usuario actual.\n\n"
            f"Usuario: {username}\n"
            f"Carpeta raiz: {self._output_root()}",
        )
        if answer != QMessageBox.Yes:
            return

        if self.client:
            self.client.logout()
        removed = clear_user_databases(self._output_root(), username)
        self.client = None
        self.token = None
        self.user = None
        self.username.clear()
        self.password.clear()
        self.office_combo.clear()
        self.scope_combo.clear()
        self.scope_combo.addItem("Personal", "personal")
        self.config.last_username = ""
        save_config(self.config)
        self.username.setEnabled(True)
        self.change_user_button.setEnabled(False)
        self.logout_button.setEnabled(False)
        self.start_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self._clear_preview()
        self._update_action_buttons()
        self._append_log(f"Cambio de usuario habilitado. Bases eliminadas: {len(removed)}.")

    def login(self) -> None:
        if not self.ensure_service_url():
            return
        self.config = self._read_config_values()
        save_config(self.config)
        self.client = SgdApiClient(self.config.service_url)
        try:
            payload = self.client.login(self.username.text().strip(), self.password.text())
        except SgdApiError as exc:
            QMessageBox.warning(self, "Login", str(exc))
            return
        self.token = payload["token"]
        self.config.last_username = self._active_username()
        save_config(self.config)
        self._set_logged_in(payload)
        self._append_log("Sesión iniciada.")

    def ensure_service_url(self) -> bool:
        service_url = self.config.service_url.strip()
        if service_url:
            return True
        value, accepted = QInputDialog.getText(
            self,
            "Configurar servicio SGD",
            "URL del servicio SGD",
            text="http://localhost:8079",
        )
        if not accepted:
            return False
        value = value.strip()
        if not value.startswith(("http://", "https://")):
            QMessageBox.warning(
                self,
                "Configurar servicio SGD",
                "La URL debe iniciar con http:// o https://.",
            )
            return False
        self.config.service_url = value.rstrip("/")
        try:
            save_config(self.config)
        except OSError as exc:
            QMessageBox.critical(
                self,
                "Configurar servicio SGD",
                f"No se pudo guardar la configuracion del servicio: {exc}",
            )
            return False
        self._append_log("URL SGD guardada junto al ejecutable.")
        return True

    def logout(self) -> None:
        if self.client:
            self.client.logout()
        self._set_logged_out()
        self._append_log("Sesión cerrada.")

    def start_download(self) -> None:
        if not self.token:
            QMessageBox.warning(self, "Descarga", "Debe iniciar sesión.")
            return
        if not self._active_username():
            QMessageBox.warning(self, "Descarga", "Debe ingresar usuario.")
            return

        office = self.office_combo.currentData()
        if not office:
            QMessageBox.warning(self, "Descarga", "Debe seleccionar una oficina.")
            return

        self.config = self._read_config_values()
        output = self._active_output_dir()
        output_text = str(output)
        if not output_text:
            QMessageBox.warning(self, "Descarga", "Debe seleccionar una carpeta destino.")
            return

        save_config(self.config)

        options = DownloadOptions(
            service_url=self.config.service_url,
            token=self.token,
            output_dir=output,
            scope=self.scope_combo.currentData(),
            depe_id=int(office["depe_id"]),
            period=self.config.period,
            per_page=self.config.per_page,
            group_size=self.config.group_size,
            include_related=self.config.include_related,
            include_personal_for_office=self.config.include_personal_for_office,
            related_batch_size=self.config.related_batch_size,
        )

        self._set_progress_running()
        self.progress.setRange(0, 0)
        self.preview_sheets_data = []
        self.start_button.setEnabled(False)
        self.export_button.setEnabled(False)
        self.clear_db_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self._append_log(f"Iniciando descarga de registros del periodo {self.config.period}.")
        self._append_log(f"Carpeta activa: {output}")
        self._append_log("Los archivos se descargan despues, desde la base local, con 'Descargar archivos'.")

        self.worker = DownloadThread(options)
        self.worker.log_message.connect(self._append_log)
        self.worker.progress_changed.connect(self._update_progress)
        self.worker.completed.connect(self._download_completed)
        self.worker.failed.connect(self._download_failed)
        self.worker.start()
        self._update_action_buttons()

    def start_file_download(self) -> None:
        if not self.token:
            QMessageBox.warning(self, "Descargar archivos", "Debe iniciar sesion.")
            return
        office = self.office_combo.currentData()
        if not office:
            QMessageBox.warning(self, "Descargar archivos", "Debe seleccionar una oficina.")
            return
        if not self._active_database_has_data():
            QMessageBox.warning(self, "Descargar archivos", "No hay registros locales para el contexto seleccionado.")
            return

        self.config = self._read_config_values()
        output = self._active_output_dir()
        options = DownloadOptions(
            service_url=self.config.service_url,
            token=self.token,
            output_dir=output,
            scope=str(self.scope_combo.currentData()),
            depe_id=int(office["depe_id"]),
            period=self.config.period,
            per_page=self.config.per_page,
            group_size=self.config.group_size,
            include_related=self.config.include_related,
            include_personal_for_office=self.config.include_personal_for_office,
            related_batch_size=self.config.related_batch_size,
        )
        self._set_progress_running()
        self.progress.setRange(0, 0)
        self._append_log("Iniciando descarga de archivos desde el catalogo local.")
        self.worker = FileDownloadThread(options)
        self.worker.log_message.connect(self._append_log)
        self.worker.progress_changed.connect(self._update_progress)
        self.worker.completed.connect(self._file_download_completed)
        self.worker.failed.connect(self._download_failed)
        self.worker.start()
        self._update_action_buttons()

    def export_excel(self) -> None:
        office = self.office_combo.currentData()
        if not office:
            QMessageBox.warning(self, "Exportar Excel", "Debe seleccionar una oficina.")
            return
        if not self._active_username():
            QMessageBox.warning(self, "Exportar Excel", "Debe ingresar usuario.")
            return

        self.config = self._read_config_values()
        output = self._active_output_dir()
        output_text = str(output)
        if not output_text:
            QMessageBox.warning(self, "Exportar Excel", "Debe seleccionar una carpeta destino.")
            return

        save_config(self.config)
        db_path = database_path(output)
        if not db_path.exists():
            QMessageBox.warning(self, "Exportar Excel", f"No existe la base local: {db_path}")
            return

        excel_file = report_path(
            output,
            period=self.config.period,
            scope=self.scope_combo.currentData(),
            depe_id=int(office["depe_id"]),
        )
        try:
            records = export_report(
                db_path,
                excel_file,
                period=self.config.period,
                scope=self.scope_combo.currentData(),
                depe_id=int(office["depe_id"]),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Exportar Excel", str(exc))
            self._append_log(f"Error exportando Excel: {exc}")
            return

        self._append_log(f"Excel generado: {excel_file}")
        self._append_log(f"Registros exportados: {records}.")
        self.load_preview()

    def clear_local_database(self) -> None:
        if not self._active_username():
            QMessageBox.warning(self, "Limpiar base", "Debe ingresar usuario.")
            return
        output = self._active_output_dir()
        if not str(output):
            QMessageBox.warning(self, "Limpiar base", "Debe seleccionar una carpeta destino.")
            return

        db_path = database_path(output)
        answer = QMessageBox.question(
            self,
            "Limpiar base",
            f"Se eliminara la base local:\n{db_path}\n\n"
            "No se eliminaran los archivos descargados, su catalogo ni los archivos Excel.",
        )
        if answer != QMessageBox.Yes:
            return

        try:
            removed = clear_database(output)
        except OSError as exc:
            QMessageBox.critical(self, "Limpiar base", str(exc))
            self._append_log(f"Error limpiando base local: {exc}")
            return

        if removed:
            self._append_log(f"Base local eliminada: {db_path}")
        else:
            self._append_log(f"No habia base local para eliminar: {db_path}")
        self._clear_preview()

    def cancel_download(self) -> None:
        if self.worker:
            self.worker.stop()
            self._append_log("Cancelando al finalizar la operación actual.")

    def _release_worker(self) -> None:
        if self.worker:
            self.worker.wait()
        self.worker = None

    def _download_completed(self, stats) -> None:
        self._release_worker()
        self._set_progress_done()
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        if stats.records_total:
            self.progress.setRange(0, stats.records_total)
            final_processed = min(max(stats.records_processed, stats.records_total), stats.records_total)
            self.progress.setValue(final_processed)
            self.progress.setFormat(f"{final_processed}/{stats.records_total}")
        self._append_log(
            "Finalizado. "
            f"Documentos: {stats.documents}, "
            f"relacionados: {stats.related_documents}, "
            f"sin relacion: {stats.related_missing_master_id}, "
            f"relacion inconsistente: {stats.related_mismatched_relation}, "
            f"descargados: {stats.files_downloaded}, "
            f"omitidos: {stats.files_skipped}, "
            f"errores: {stats.files_failed}."
        )
        if stats.database_file:
            self._append_log(f"Base local: {stats.database_file}")
        self._update_action_buttons()
        self.load_preview()

    def _file_download_completed(self, stats) -> None:
        self._release_worker()
        if stats.files_failed:
            self._set_progress_error()
        else:
            self._set_progress_done()
        if stats.files_total:
            self.progress.setRange(0, stats.files_total)
            self.progress.setValue(stats.files_total)
            self.progress.setFormat(f"{stats.files_total}/{stats.files_total} - Archivos revisados")
        else:
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
            self.progress.setFormat("0/0 - Sin archivos adjuntos")
        self._append_log(
            "Archivos finalizados. "
            f"Descargados: {stats.files_downloaded}, "
            f"omitidos: {stats.files_skipped}, errores: {stats.files_failed}."
        )
        if stats.catalog_file:
            self._append_log(f"Catalogo de archivos: {stats.catalog_file}")
        self._update_action_buttons()

    def _update_progress(self, processed: int, total: int, label: str) -> None:
        self._set_progress_running()
        if total <= 0:
            self.progress.setRange(0, 0)
            return
        self.progress.setRange(0, total)
        self.progress.setValue(min(processed, total))
        self.progress.setFormat(f"{processed}/{total} - {label}")

    def _download_failed(self, message: str) -> None:
        self._release_worker()
        self._set_progress_error()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        QMessageBox.critical(self, "Descarga", message)
        self._append_log(f"Error: {message}")
        self._update_action_buttons()

    def _set_progress_running(self) -> None:
        self.progress.setStyleSheet(PROGRESS_STYLE_RUNNING)

    def _set_progress_done(self) -> None:
        self.progress.setStyleSheet(PROGRESS_STYLE_DONE)

    def _set_progress_error(self) -> None:
        self.progress.setStyleSheet(PROGRESS_STYLE_ERROR)

    def _reset_progress_empty(self) -> None:
        self.progress.setStyleSheet("")
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setFormat("0%")

    def _set_progress_data_available(self) -> None:
        total_records = sum(int(total or 0) for _name, total, _rows in self.preview_sheets_data)
        self._set_progress_done()
        self.progress.setRange(0, max(1, total_records))
        self.progress.setValue(max(1, total_records))
        self.progress.setFormat(f"{total_records}/{total_records}")

    def _append_log(self, message: str) -> None:
        self.log.append(message)
        try:
            APP_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with LOG_FILE.open("a", encoding="utf-8") as handle:
                handle.write(f"{timestamp} {message}\n")
        except OSError:
            pass

    def _toggle_log(self, checked: bool) -> None:
        self.log.setVisible(checked)
        self.log_toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)

    def load_preview(self) -> None:
        self.preview_request_id += 1
        request_id = self.preview_request_id
        self.preview_sheets_data = []
        self._update_action_buttons()
        office = self.office_combo.currentData()
        if not office:
            self._clear_preview()
            self._reset_progress_empty()
            return
        config = self._read_config_values()
        if not self._active_username():
            self._clear_preview()
            self._reset_progress_empty()
            return
        db_path = database_path(self._active_output_dir(str(self.scope_combo.currentData() or "personal")))
        if not db_path.exists():
            self._clear_preview()
            self._reset_progress_empty()
            return

        self.related_button.setEnabled(False)
        self.preview_status.setText("Cargando vista previa...")
        worker = PreviewThread(
            request_id,
            db_path,
            config.period,
            str(self.scope_combo.currentData()),
            int(office["depe_id"]),
        )
        worker.loaded.connect(self._preview_loaded)
        worker.failed.connect(self._preview_failed)
        worker.finished.connect(lambda: self._preview_worker_finished(worker))
        self.preview_workers.append(worker)
        worker.start()

    def _preview_loaded(self, request_id: int, sheets: object) -> None:
        if request_id != self.preview_request_id:
            return
        self.preview_sheets_data = sheets
        self.sheet_combo.blockSignals(True)
        self.sheet_combo.clear()
        for name, total, _rows in self.preview_sheets_data:
            self.sheet_combo.addItem(f"{name} ({total})")
        self.sheet_combo.blockSignals(False)
        self._show_preview_sheet(0)
        if not self._is_downloading():
            if self._preview_has_records():
                self._set_progress_data_available()
            else:
                self._reset_progress_empty()
        self._update_action_buttons()

    def _preview_failed(self, request_id: int, message: str) -> None:
        if request_id != self.preview_request_id:
            return
        self._clear_preview()
        self._append_log(f"No se pudo cargar vista previa: {message}")
        self._update_action_buttons()

    def _preview_worker_finished(self, worker: PreviewThread) -> None:
        if worker in self.preview_workers:
            self.preview_workers.remove(worker)

    def _show_preview_sheet(self, index: int) -> None:
        if index < 0 or index >= len(self.preview_sheets_data):
            self.preview_table.clear()
            self.preview_table.setRowCount(0)
            self.preview_table.setColumnCount(0)
            return

        _, total_rows, rows = self.preview_sheets_data[index]
        if not rows:
            self._clear_preview()
            return

        headers = [str(value) for value in rows[0]]
        data_rows = rows[1:]
        self.preview_table.setColumnCount(len(headers))
        self.preview_table.setRowCount(len(data_rows))
        self.preview_table.setHorizontalHeaderLabels(headers)
        self.preview_table.setUpdatesEnabled(False)
        try:
            for row_index, row in enumerate(data_rows):
                for col_index, value in enumerate(row):
                    self.preview_table.setItem(row_index, col_index, QTableWidgetItem(str(value or "")))
            self.preview_table.hideColumn(0)
            self.preview_table.setColumnWidth(1, 90)
            self.preview_table.setColumnWidth(2, 160)
            self.preview_table.setColumnWidth(3, 90)
            self.preview_table.setColumnWidth(4, 420)
            self.preview_table.setColumnWidth(5, 220)
            self.preview_table.setColumnWidth(6, 180)
            self.preview_table.setColumnWidth(7, 70)
            self.preview_table.setColumnWidth(8, 95)
            self.preview_table.setColumnWidth(9, 70)
            self.preview_table.setColumnWidth(10, 180)
            self.preview_table.setColumnWidth(11, 90)
        finally:
            self.preview_table.setUpdatesEnabled(True)
        self.related_button.setEnabled(bool(data_rows))
        if total_rows > len(data_rows):
            self.preview_status.setText(f"Mostrando {PREVIEW_ROW_LIMIT} de {total_rows} principales. El Excel exportara todos.")
        else:
            self.preview_status.setText(f"Mostrando {total_rows} principales.")

    def _clear_preview(self) -> None:
        self.preview_request_id += 1
        self.preview_sheets_data = []
        self.sheet_combo.blockSignals(True)
        self.sheet_combo.clear()
        self.sheet_combo.blockSignals(False)
        self.preview_table.clear()
        self.preview_table.setRowCount(0)
        self.preview_table.setColumnCount(0)
        self.preview_status.setText("")
        self.related_button.setEnabled(False)
        self._update_action_buttons()

    def open_related_documents(self) -> None:
        row = self.preview_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Relacionados", "Debe seleccionar un documento principal.")
            return
        id_item = self.preview_table.item(row, 0)
        if not id_item:
            QMessageBox.information(self, "Relacionados", "No se encontro el ID del documento seleccionado.")
            return
        try:
            master_id = int(id_item.text())
        except ValueError:
            QMessageBox.information(self, "Relacionados", "El ID del documento seleccionado no es valido.")
            return

        office = self.office_combo.currentData()
        if not office:
            return
        config = self._read_config_values()
        db_path = database_path(self._active_output_dir(str(self.scope_combo.currentData() or "personal")))
        try:
            total_related = related_count(
                db_path,
                master_id=master_id,
                period=config.period,
                scope=self.scope_combo.currentData(),
                depe_id=int(office["depe_id"]),
            )
            rows = related_preview_rows(
                db_path,
                master_id=master_id,
                period=config.period,
                scope=self.scope_combo.currentData(),
                depe_id=int(office["depe_id"]),
                limit=RELATED_ROW_LIMIT,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Relacionados", str(exc))
            self._append_log(f"Error cargando relacionados: {exc}")
            return
        if total_related <= 0:
            QMessageBox.information(self, "Relacionados", "El documento seleccionado no tiene relacionados.")
            return
        if total_related > RELATED_ROW_LIMIT:
            self._append_log(
                f"Relacionados de {master_id}: mostrando {RELATED_ROW_LIMIT} de {total_related} registros."
            )
        dialog = RelatedDialog(f"Relacionados de {master_id}", rows, self)
        dialog.exec()

    def closeEvent(self, event) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            if not self.worker.wait(60000):
                self._append_log(
                    "No se pudo cancelar la descarga en curso a tiempo; vuelva a cerrar la ventana."
                )
                event.ignore()
                return
        for worker in list(self.preview_workers):
            if worker.isRunning() and not worker.wait(60000):
                self._append_log(
                    "No se pudo cancelar la vista previa en curso a tiempo; vuelva a cerrar la ventana."
                )
                event.ignore()
                return
        if self.client:
            self.client.logout()
        event.accept()


def run_app() -> int:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    window.ensure_service_url()
    return app.exec()
