"""
main_window.py
--------------
Options+-inspired NISSOU Macro Pad Configurator.

The physical 3x3 Macro Pad is the primary interaction surface: click a key
or the rotary encoder in the device preview and configure it in the panel on
the right. Existing profile, serial and firmware-protocol behavior is kept.
"""

import ctypes
import os
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QInputDialog, QMessageBox, QPlainTextEdit, QSplitter,
    QLineEdit, QListWidget, QListWidgetItem, QScrollArea, QFrame,
    QGraphicsOpacityEffect, QToolButton, QSizePolicy, QDialog,
)

from .protocol import Profile, commands_for_profile
from .profile_store import list_profile_names, save_profile, load_profile, delete_profile
from .serial_link import SerialLink, find_candidate_ports
from .widgets import (
    AssignmentPanel, EncoderPanel, MacroPadPreview, LogoMark, StatusDot, AppChip,
)


APP_TITLE = "NISSOU Macro Pad Configurator"


def foreground_process_name():
    if os.name != "nt":
        return ""
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    process_id = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
    handle = kernel32.OpenProcess(0x1000 | 0x0010, False, process_id.value)
    if not handle:
        return ""
    try:
        buffer = ctypes.create_unicode_buffer(260)
        length = ctypes.c_ulong(len(buffer))
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(length)):
            return ""
        return Path(buffer.value).name.lower()
    finally:
        kernel32.CloseHandle(handle)


def open_window_process_names():
    if os.name != "nt":
        return []

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    names = set()
    enum_windows = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def collect_window(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd) or user32.IsIconic(hwnd):
            return True
        if user32.GetWindowTextLengthW(hwnd) == 0:
            return True

        process_id = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        handle = kernel32.OpenProcess(0x1000 | 0x0010, False, process_id.value)
        if not handle:
            return True
        try:
            buffer = ctypes.create_unicode_buffer(260)
            length = ctypes.c_ulong(len(buffer))
            if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(length)):
                names.add(Path(buffer.value).name.lower())
        finally:
            kernel32.CloseHandle(handle)
        return True

    user32.EnumWindows(enum_windows(collect_window), 0)
    return sorted(names)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1240, 780)
        self.setMinimumSize(900, 600)

        self.serial = SerialLink()
        self.serial.connected.connect(self._on_connected)
        self.serial.disconnected.connect(self._on_disconnected)
        self.serial.error.connect(self._on_error)
        self.serial.command_result.connect(self._on_command_result)
        self.serial.encoder_event.connect(self._on_encoder_device_event)
        self.serial.log.connect(self._append_log)

        self.current_profile = Profile(name="Default")
        self._pending_commands = []
        self._content_effect = None
        self._auto_profile_name = ""
        self._selected_key = 1

        self._build_ui()
        self._refresh_profile_list()
        self._load_selected_profile(animate=False)

        self._app_watch = QTimer(self)
        self._app_watch.setInterval(500)
        self._app_watch.timeout.connect(self._check_active_app)
        self._app_watch.start()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)

        sidebar = self._build_sidebar()
        sidebar.setMinimumWidth(280)
        sidebar.setMaximumWidth(380)
        splitter.addWidget(sidebar)

        content_scroll = self._build_content()
        splitter.addWidget(content_scroll)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        outer.addWidget(splitter, stretch=1)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(100)
        self.log_view.setObjectName("logView")
        self._log_box = self._wrap_card("Device Log", self.log_view, collapsible=True)
        outer.addWidget(self._log_box)

        self.assignment_panel.binding_changed.connect(self._on_key_changed)
        self.assignment_panel.set_dialog_callback(self._configure_selected_key)
        self.encoder_panel.encoder_changed.connect(self._on_encoder_changed)
        self.encoder_panel.sensitivity_changed.connect(self._on_sensitivity_changed)

    # --------------------------------------------------------------- sidebar
    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 20, 18, 18)
        layout.setSpacing(16)

        brand_row = QHBoxLayout()
        brand_row.addWidget(LogoMark())
        brand_copy = QVBoxLayout()
        brand_copy.setSpacing(0)
        title = QLabel("NISSOU")
        title.setObjectName("brandTitle")
        subtitle = QLabel("MACRO DECK")
        subtitle.setObjectName("brandSubtitle")
        brand_copy.addWidget(title)
        brand_copy.addWidget(subtitle)
        brand_row.addLayout(brand_copy)
        brand_row.addStretch(1)
        brand_widget = QWidget()
        brand_widget.setLayout(brand_row)
        layout.addWidget(brand_widget)

        opacity = QGraphicsOpacityEffect(brand_widget)
        brand_widget.setGraphicsEffect(opacity)
        self.brand_animation = QPropertyAnimation(opacity, b"opacity", self)
        self.brand_animation.setDuration(600)
        self.brand_animation.setStartValue(0.0)
        self.brand_animation.setEndValue(1.0)
        self.brand_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        QTimer.singleShot(50, self.brand_animation.start)

        layout.addWidget(self._build_connection_card())

        section_label = QLabel("PROFILES")
        section_label.setObjectName("sectionLabel")
        layout.addWidget(section_label)

        self.profile_list = QListWidget()
        self.profile_list.setObjectName("profileList")
        self.profile_list.currentTextChanged.connect(self._on_profile_selected)
        layout.addWidget(self.profile_list, stretch=1)

        profile_actions = QHBoxLayout()
        new_btn = QPushButton("New")
        new_btn.clicked.connect(self._new_profile)
        rename_btn = QPushButton("Rename")
        rename_btn.clicked.connect(self._rename_profile)
        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("dangerButton")
        delete_btn.clicked.connect(self._delete_profile)
        profile_actions.addWidget(new_btn)
        profile_actions.addWidget(rename_btn)
        profile_actions.addWidget(delete_btn)
        layout.addLayout(profile_actions)

        return sidebar

    def _build_connection_card(self):
        card = QFrame()
        card.setObjectName("connectionCard")
        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        status_row = QHBoxLayout()
        self.status_dot = StatusDot()
        self.status_dot.set_state("disconnected")
        status_row.addWidget(self.status_dot)
        self.status_label = QLabel("Disconnected")
        self.status_label.setObjectName("statusLabel")
        status_row.addWidget(self.status_label)
        status_row.addStretch(1)
        layout.addLayout(status_row)

        self.port_combo = QComboBox()
        layout.addWidget(self.port_combo)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_ports)
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("primaryButton")
        self.connect_btn.clicked.connect(self._toggle_connection)
        btn_row.addWidget(refresh_btn)
        btn_row.addWidget(self.connect_btn)
        layout.addLayout(btn_row)

        self._refresh_ports()
        return card

    # --------------------------------------------------------------- content
    def _build_content(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("contentScroll")

        content = QWidget()
        content.setObjectName("contentArea")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)
        scroll.setWidget(content)

        header_card = QFrame()
        header_card.setObjectName("card")
        header_layout = QVBoxLayout(header_card)

        title_row = QHBoxLayout()
        self.profile_title = QLabel("Profile")
        self.profile_title.setObjectName("profileTitle")
        title_row.addWidget(self.profile_title)
        title_row.addStretch(1)

        self.save_local_btn = QPushButton("Save Profile")
        self.save_local_btn.clicked.connect(self._save_current_profile)
        self.push_btn = QPushButton("Push to Macro Pad")
        self.push_btn.setObjectName("primaryButton")
        self.push_btn.clicked.connect(self._push_to_device)
        self.push_btn.setEnabled(False)
        title_row.addWidget(self.save_local_btn)
        title_row.addWidget(self.push_btn)
        header_layout.addLayout(title_row)

        app_row = QHBoxLayout()
        app_label = QLabel("Auto-switch when this app is active:")
        app_row.addWidget(app_label)
        self.app_match_edit = QComboBox()
        self.app_match_edit.setEditable(True)
        self.app_match_edit.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.app_match_edit.setPlaceholderText("Spotify.exe or brave.exe")
        self.app_match_edit.setToolTip("Automatically use this profile when this process is active")
        self.app_match_edit.setMinimumWidth(200)
        self.app_match_edit.lineEdit().editingFinished.connect(self._save_app_match)
        app_row.addWidget(self.app_match_edit, stretch=1)
        refresh_apps_btn = QPushButton("Open apps")
        refresh_apps_btn.setToolTip("Show currently open visible applications")
        refresh_apps_btn.clicked.connect(self._refresh_open_apps)
        app_row.addWidget(refresh_apps_btn)
        header_layout.addLayout(app_row)

        # Visual app targets: recognizable tiles for common profile targets.
        apps_row = QHBoxLayout()
        apps_label = QLabel("Quick app targets")
        apps_label.setObjectName("mutedLabel")
        apps_row.addWidget(apps_label)
        self.spotify_chip = AppChip("Spotify", "spotify.exe")
        self.spotify_chip.clicked_app.connect(self._select_app_target)
        apps_row.addWidget(self.spotify_chip)
        self.vscode_chip = AppChip("Visual Studio Code", "code.exe")
        self.vscode_chip.clicked_app.connect(self._select_app_target)
        apps_row.addWidget(self.vscode_chip)
        apps_row.addStretch(1)
        header_layout.addLayout(apps_row)

        layout.addWidget(header_card)

        # Main Options+-style device editor: physical preview on the left,
        # selected key/encoder configuration on the right.
        editor_card = QFrame()
        editor_card.setObjectName("card")
        editor_layout = QVBoxLayout(editor_card)
        editor_layout.setContentsMargins(14, 14, 14, 14)
        editor_layout.setSpacing(0)

        editor_splitter = QSplitter(Qt.Orientation.Horizontal)
        editor_splitter.setObjectName("editorSplitter")
        editor_splitter.setChildrenCollapsible(False)
        editor_splitter.setHandleWidth(1)

        preview_column = QVBoxLayout()
        preview_label = QLabel("Your Macro Pad")
        preview_label.setObjectName("sectionLabel")
        preview_column.addWidget(preview_label)

        self.pad_preview = MacroPadPreview()
        self.pad_preview.key_clicked.connect(self._on_preview_key_clicked)
        self.pad_preview.encoder_clicked.connect(self._on_preview_encoder_clicked)
        preview_column.addWidget(self.pad_preview, stretch=1)

        hint = QLabel("Click a key or the rotary encoder to configure it.")
        hint.setObjectName("dialogHint")
        preview_column.addWidget(hint)
        preview_widget = QWidget()
        preview_widget.setLayout(preview_column)
        preview_widget.setMinimumWidth(620)
        editor_splitter.addWidget(preview_widget)

        right_column = QVBoxLayout()
        right_column.setSpacing(12)

        self.assignment_panel = AssignmentPanel()
        right_column.addWidget(self.assignment_panel, stretch=1)

        self.encoder_panel = EncoderPanel()
        right_column.addWidget(self.encoder_panel, stretch=1)

        right_widget = QWidget()
        right_widget.setLayout(right_column)
        right_widget.setMinimumWidth(350)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_scroll.setWidget(right_widget)
        editor_splitter.addWidget(right_scroll)
        editor_splitter.setStretchFactor(0, 3)
        editor_splitter.setStretchFactor(1, 2)
        editor_splitter.setSizes([620, 360])
        editor_layout.addWidget(editor_splitter)
        layout.addWidget(editor_card, stretch=1)

        layout.addStretch(1)

        self._content_effect = QGraphicsOpacityEffect(content)
        self._content_effect.setOpacity(1.0)
        content.setGraphicsEffect(self._content_effect)

        return scroll

    def _wrap_card(self, title, widget, collapsible=False):
        box = QFrame()
        box.setObjectName("card")
        layout = QVBoxLayout(box)
        header = QHBoxLayout()
        label = QLabel(title)
        label.setObjectName("sectionLabel")
        header.addWidget(label)
        header.addStretch(1)
        if collapsible:
            toggle = QToolButton()
            toggle.setText("Hide")
            toggle.setCheckable(True)
            toggle.setChecked(True)

            def _on_toggle(checked):
                widget.setVisible(checked)
                toggle.setText("Hide" if checked else "Show")

            toggle.toggled.connect(_on_toggle)
            header.addWidget(toggle)
        layout.addLayout(header)
        layout.addWidget(widget)
        return box

    # ------------------------------------------------------- port/connect
    def _refresh_ports(self):
        self.port_combo.clear()
        ports = find_candidate_ports()
        if not ports:
            self.port_combo.addItem("SIMULATED (no device found)", "SIM")
        else:
            for device, desc in ports:
                self.port_combo.addItem(f"{device} — {desc}", device)

    def _toggle_connection(self):
        if self.connect_btn.text() == "Connect":
            port = self.port_combo.currentData() or "SIM"
            self.status_dot.set_state("connecting")
            self.status_label.setText("Connecting…")
            self.connect_btn.setEnabled(False)
            self._append_log(f"Connecting to {port}...")
            self.serial.connect_to(port)
        else:
            self.serial.disconnect()

    def _on_connected(self, port, firmware):
        self.status_dot.set_state("connected")
        self.status_label.setText(f"Connected · {port}")
        self.status_label.setToolTip(f"Firmware {firmware}")
        self.connect_btn.setText("Disconnect")
        self.connect_btn.setEnabled(True)
        self.push_btn.setEnabled(True)
        self.pad_preview.set_connected(True)

    def _on_disconnected(self):
        self.status_dot.set_state("disconnected")
        self.status_label.setText("Disconnected")
        self.connect_btn.setText("Connect")
        self.connect_btn.setEnabled(True)
        self.push_btn.setEnabled(False)
        self.pad_preview.set_connected(False)

    def _on_error(self, message):
        self.status_dot.set_state("error")
        self.status_label.setText("Connection error")
        self.connect_btn.setText("Connect")
        self.connect_btn.setEnabled(True)
        self._append_log(f"ERROR: {message}")

    def _on_command_result(self, cmd, ok, reply):
        pass

    def _on_encoder_device_event(self, event):
        if event != "PRESS":
            return
        names = list_profile_names()
        if len(names) < 2:
            self._append_log("Encoder profile switch needs at least two profiles.")
            return
        current = self._current_profile_name()
        next_index = (names.index(current) + 1) % len(names) if current in names else 0
        next_name = names[next_index]
        profile = load_profile(next_name)
        self._select_profile_by_name(next_name)
        self._apply_profile_to_ui(profile)
        self._push_profile_runtime(profile)
        self._append_log(f"Encoder button switched to profile '{next_name}'.")

    def _append_log(self, text):
        self.log_view.appendPlainText(text)

    # ------------------------------------------------------------ profiles
    def _refresh_profile_list(self):
        self.profile_list.blockSignals(True)
        self.profile_list.clear()
        names = list_profile_names()
        for name in names:
            self.profile_list.addItem(QListWidgetItem(name))
        if names:
            self.profile_list.setCurrentRow(0)
        self.profile_list.blockSignals(False)

    def _current_profile_name(self):
        item = self.profile_list.currentItem()
        return item.text() if item else ""

    def _select_profile_by_name(self, name):
        for row in range(self.profile_list.count()):
            if self.profile_list.item(row).text() == name:
                self.profile_list.blockSignals(True)
                self.profile_list.setCurrentRow(row)
                self.profile_list.blockSignals(False)
                return

    def _apply_profile_to_ui(self, profile):
        self.current_profile = profile
        self.profile_title.setText(profile.name)
        self.pad_preview.set_keys(profile.keys)
        self.pad_preview.set_encoder(profile.encoder)
        self.assignment_panel.set_selection(
            self._selected_key,
            profile.keys.get(self._selected_key, ""),
        )
        self.encoder_panel.load_encoder(profile.encoder, profile.sensitivity)
        self.app_match_edit.blockSignals(True)
        self.app_match_edit.setCurrentText(profile.app_match)
        self.app_match_edit.blockSignals(False)

    def _load_selected_profile(self, animate=True):
        name = self._current_profile_name()
        if not name:
            return

        def apply():
            self._apply_profile_to_ui(load_profile(name))

        if animate:
            self._animate_profile_switch(apply)
        else:
            apply()

    def _animate_profile_switch(self, apply_fn):
        fade_out = QPropertyAnimation(self._content_effect, b"opacity", self)
        fade_out.setDuration(110)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.25)
        fade_out.setEasingCurve(QEasingCurve.Type.InCubic)

        def _on_faded_out():
            apply_fn()
            fade_in = QPropertyAnimation(self._content_effect, b"opacity", self)
            fade_in.setDuration(180)
            fade_in.setStartValue(0.25)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
            fade_in.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
            self._fade_in_anim = fade_in

        fade_out.finished.connect(_on_faded_out)
        fade_out.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._fade_out_anim = fade_out

    def _on_profile_selected(self, _name):
        self._load_selected_profile()

    def _new_profile(self):
        name, ok = QInputDialog.getText(self, "New Profile", "Profile name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        profile = Profile(name=name)
        save_profile(profile)
        self._refresh_profile_list()
        self._select_profile_by_name(name)
        self._load_selected_profile()

    def _rename_profile(self):
        old_name = self._current_profile_name()
        if not old_name:
            return
        new_name, ok = QInputDialog.getText(
            self, "Rename Profile", "New name:", QLineEdit.Normal, old_name
        )
        if not ok or not new_name.strip() or new_name.strip() == old_name:
            return
        new_name = new_name.strip()
        self.current_profile.name = new_name
        save_profile(self.current_profile)
        delete_profile(old_name)
        self._refresh_profile_list()
        self._select_profile_by_name(new_name)
        self._load_selected_profile()

    def _delete_profile(self):
        name = self._current_profile_name()
        if not name:
            return
        if QMessageBox.question(self, "Delete Profile", f"Delete '{name}'?") != QMessageBox.Yes:
            return
        delete_profile(name)
        self._refresh_profile_list()
        self._load_selected_profile()

    def _save_current_profile(self):
        self._save_app_match()
        self.current_profile.keys = dict(self.current_profile.keys)
        self.current_profile.encoder = self.encoder_panel.current_encoder()
        self.current_profile.sensitivity = self.encoder_panel.current_sensitivity()
        save_profile(self.current_profile)
        self._append_log(f"Saved profile '{self.current_profile.name}' locally.")

    def _save_app_match(self):
        if hasattr(self, "app_match_edit"):
            self.current_profile.app_match = self.app_match_edit.currentText().strip().lower()
            save_profile(self.current_profile)

    def _refresh_open_apps(self):
        current = self.app_match_edit.currentText()
        self.app_match_edit.blockSignals(True)
        self.app_match_edit.clear()
        self.app_match_edit.addItem("")
        self.app_match_edit.addItems(open_window_process_names())
        self.app_match_edit.setCurrentText(current)
        self.app_match_edit.blockSignals(False)

    def _select_app_target(self, executable):
        self.app_match_edit.setCurrentText(executable)
        self._save_app_match()
        self._append_log(f"Profile app target: {executable}")

    def _configure_selected_key(self, index=None):
        index = index or self._selected_key
        binding = self.current_profile.keys.get(index, "")
        from .widgets import KeyBindDialog
        dlg = KeyBindDialog(binding, f"Key {index}", self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._on_key_changed(index, dlg.value())

    # ------------------------------------------------------ preview/editor
    def _on_preview_key_clicked(self, index):
        self._selected_key = index
        binding = self.current_profile.keys.get(index, "")
        self.assignment_panel.set_selection(index, binding)
        self.pad_preview.set_selected_key(index)
        self._append_log(f"Selected Key {index}.")

    def _on_preview_encoder_clicked(self):
        self.pad_preview.select_encoder()
        self._append_log("Selected rotary encoder.")
        self.encoder_panel.setFocus()

    def _on_key_changed(self, index, binding):
        self.current_profile.keys[index] = binding
        self.pad_preview.set_keys(self.current_profile.keys)
        self.pad_preview.set_selected_key(index)
        self._selected_key = index
        self._append_log(f"Key {index} assigned: {binding or 'Unassigned'}")

    def _on_encoder_changed(self, event, action):
        self.current_profile.encoder[event] = action
        self.pad_preview.set_encoder(self.current_profile.encoder)

    def _on_sensitivity_changed(self, value):
        self.current_profile.sensitivity = value

    # ------------------------------------------------------------- push
    def _push_profile_runtime(self, profile):
        for cmd in commands_for_profile(profile, include_save=False):
            self.serial.send_command(cmd)

    def _check_active_app(self):
        active_app = foreground_process_name()
        if not active_app or active_app == self._auto_profile_name:
            return
        self._auto_profile_name = active_app

        for name in list_profile_names():
            profile = load_profile(name)
            if profile.app_match.strip().lower() != active_app:
                continue
            self._apply_profile_to_ui(profile)
            self._select_profile_by_name(name)
            if self.push_btn.isEnabled():
                self._push_profile_runtime(profile)
            self._append_log(f"Auto profile: {name} ({active_app})")
            return

    def _push_to_device(self):
        self._save_app_match()
        self.current_profile.keys = dict(self.current_profile.keys)
        self.current_profile.encoder = self.encoder_panel.current_encoder()
        self.current_profile.sensitivity = self.encoder_panel.current_sensitivity()
        save_profile(self.current_profile)

        self._append_log(f"Pushing profile '{self.current_profile.name}' to device...")
        for cmd in commands_for_profile(self.current_profile):
            self.serial.send_command(cmd)

    def closeEvent(self, event):
        self.serial.shutdown()
        super().closeEvent(event)
