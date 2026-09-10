"""
widgets.py
NISSOU Macro Pad Configurator
Modern hardware-first UI inspired by Logitech Options+.

The device preview is the primary control surface:
- click any of the 9 keys to configure it
- click the encoder to configure rotate/press actions
- OLED preview reflects the selected control
- app chips provide recognizable visual app targets
"""

from PySide6.QtCore import QEvent, QPropertyAnimation, Qt, QTimer, Property, Signal, QRectF
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPainterPath, QPen, QFont
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QSlider, QVBoxLayout, QWidget, QFrame, QScrollArea, QSizePolicy
)

from .protocol import ENCODER_EVENTS


COMMON_KEYS = [
    "CTRL+C", "CTRL+V", "CTRL+X", "CTRL+Z", "CTRL+Y", "CTRL+S", "CTRL+A",
    "ALT+TAB", "ALT+F4", "F1", "F2", "F3", "F4", "F5", "F6", "F7",
    "F8", "F9", "F10", "F11", "F12", "TAB", "SPACE", "ENTER", "ESC",
    "PRTSC", "DELETE", "HOME", "END", "UP", "DOWN", "LEFT", "RIGHT"
]

ACCENT = "#3d7bf7"
GREEN = "#1ed760"


class LogoMark(QWidget):
    def __init__(self, parent=None, size=40):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self._size
        path = QPainterPath()
        path.addRoundedRect(0, 0, s, s, s * .28, s * .28)
        p.fillPath(path, QColor(ACCENT))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("white"))
        pad = s * .22
        gap = (s - 2 * pad) / 2
        for r in range(3):
            for c in range(3):
                x, y = pad + c * gap, pad + r * gap
                d = gap * (.40 if (r, c) == (1, 1) else .30)
                p.drawEllipse(x-d/2, y-d/2, d, d)
        p.end()


class StatusDot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._color = QColor("#7d8796")
        self._anim = None

    def getColor(self):
        return self._color

    def setColor(self, color):
        self._color = color
        self.update()

    color = Property(QColor, getColor, setColor)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self._color)
        p.drawEllipse(1, 1, 10, 10)
        p.end()

    def set_state(self, state):
        if self._anim:
            self._anim.stop()
        colors = {
            "connected": QColor("#22c55e"),
            "disconnected": QColor("#7d8796"),
            "error": QColor("#ef5350")
        }
        if state == "connecting":
            self._anim = QPropertyAnimation(self, b"color", self)
            self._anim.setDuration(650)
            self._anim.setStartValue(QColor(ACCENT))
            self._anim.setKeyValueAt(.5, QColor("#d9e7ff"))
            self._anim.setEndValue(QColor(ACCENT))
            self._anim.start()
        else:
            self.setColor(colors.get(state, colors["disconnected"]))


class AppIcon(QWidget):
    """Small vector icon for common apps; no external icon assets required."""

    def __init__(self, app_name="", parent=None):
        super().__init__(parent)
        self.app_name = app_name.lower()
        self.setFixedSize(34, 34)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)

        if "spotify" in self.app_name:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#1ed760"))
            p.drawRoundedRect(r, 10, 10)
            p.setPen(QPen(QColor("#07120b"), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(QRectF(8, 9, 18, 11), 22 * 16, 136 * 16)
            p.drawArc(QRectF(10, 14, 15, 9), 22 * 16, 136 * 16)
            p.drawArc(QRectF(12, 19, 11, 6), 22 * 16, 136 * 16)
        elif "code" in self.app_name or "vscode" in self.app_name:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#1687f7"))
            path = QPainterPath()
            path.moveTo(6, 17)
            path.lineTo(14, 8)
            path.lineTo(28, 12)
            path.lineTo(28, 26)
            path.lineTo(14, 30)
            path.lineTo(6, 21)
            path.lineTo(12, 17)
            path.lineTo(21, 23)
            path.lineTo(21, 12)
            path.lineTo(12, 17)
            path.closeSubpath()
            p.drawPath(path)
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#29374b"))
            p.drawRoundedRect(r, 10, 10)
            p.setPen(QPen(QColor("#dce8fa"), 1.8))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(10, 9, 14, 14))
            p.drawLine(17, 12, 17, 18)
            p.drawLine(17, 18, 21, 20)
        p.end()


class AppChip(QPushButton):
    clicked_app = Signal(str)

    def __init__(self, name, executable, parent=None):
        super().__init__(parent)
        self.executable = executable
        self.setObjectName("appChip")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(48)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 6, 10, 6)
        row.setSpacing(9)
        row.addWidget(AppIcon(name))
        text = QVBoxLayout()
        text.setSpacing(0)
        title = QLabel(name)
        title.setObjectName("appChipTitle")
        sub = QLabel(executable)
        sub.setObjectName("appChipSub")
        text.addWidget(title)
        text.addWidget(sub)
        row.addLayout(text)
        row.addStretch(1)

        self.clicked.connect(lambda: self.clicked_app.emit(executable))


class UiIcon(QWidget):
    """Small reliable vector icon used instead of font-dependent glyphs."""

    def __init__(self, kind="dot", parent=None, size=22):
        super().__init__(parent)
        self.kind = kind
        self.setFixedSize(size, size)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#8eb9ff"), 1.8))
        p.setBrush(Qt.BrushStyle.NoBrush)
        r = self.rect().adjusted(3, 3, -3, -3)
        if self.kind == "keyboard":
            p.drawRoundedRect(r, 3, 3)
            for x in range(7, self.width() - 5, 4):
                p.drawLine(x, 9, x, 10)
            p.drawLine(7, 14, self.width() - 7, 14)
        elif self.kind == "text":
            p.setPen(QPen(QColor("#dce8fa"), 2))
            p.drawLine(self.width() / 2, 4, self.width() / 2, self.height() - 4)
            p.drawLine(6, 5, self.width() - 6, 5)
        elif self.kind == "application":
            p.drawRoundedRect(r, 2, 2)
            p.drawLine(3, 8, self.width() - 3, 8)
        elif self.kind == "system":
            p.drawLine(6, 16, self.width() - 6, 6)
            p.drawLine(self.width() - 6, 6, self.width() - 8, 12)
            p.drawLine(self.width() - 6, 6, self.width() - 12, 8)
        elif self.kind == "encoder":
            p.drawEllipse(r)
            p.drawLine(self.width() / 2, 6, self.width() / 2, 10)
        elif self.kind == "clockwise":
            p.drawArc(r, 35 * 16, 275 * 16)
            p.drawLine(self.width() - 5, 7, self.width() - 10, 7)
            p.drawLine(self.width() - 5, 7, self.width() - 7, 12)
        elif self.kind == "counterclockwise":
            p.drawArc(r, -140 * 16, 275 * 16)
            p.drawLine(5, 7, 10, 7)
            p.drawLine(5, 7, 7, 12)
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#8eb9ff"))
            p.drawEllipse(r)
        p.end()


class MacroPadPreview(QWidget):
    """Premium clickable 3x3 macro-pad representation."""

    key_clicked = Signal(int)
    encoder_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 470)
        self._selected_key = 1
        self._encoder_selected = False
        self._connected = False
        self._keys = {i: "" for i in range(1, 10)}
        self._encoder = {}
        self._sensitivity = 3
        self._pressed_key = 0
        self._pulse = 0

        self._timer = QTimer(self)
        self._timer.setInterval(70)
        self._timer.timeout.connect(self._advance)
        self._timer.start()

    def set_connected(self, connected):
        self._connected = connected
        self.update()

    def set_selected_key(self, index):
        self._selected_key = index
        self._encoder_selected = False
        self.update()

    def select_encoder(self):
        self._encoder_selected = True
        self.update()

    def load_profile(self, keys, encoder, sensitivity):
        self._keys = {i: keys.get(i, "") for i in range(1, 10)}
        self._encoder = dict(encoder or {})
        self._sensitivity = sensitivity
        self.update()

    def set_keys(self, keys):
        self._keys = {i: keys.get(i, "") for i in range(1, 10)}
        self.update()

    def set_encoder(self, encoder):
        self._encoder = dict(encoder or {})
        self.update()

    def flash_key(self, index):
        self._pressed_key = index
        self._pulse = 12
        self.update()

    def _advance(self):
        if self._pulse:
            self._pulse -= 1
            self.update()

    def _geometry(self):
        w, h = self.width(), self.height()
        body_w = min(w - 30, 680)
        body_h = min(h - 30, 440)
        bx, by = (w-body_w)/2, (h-body_h)/2

        # OLED
        ow, oh = body_w*.35, body_h*.19
        ox, oy = bx + body_w*.325, by + body_h*.065

        # keys
        key = min(body_h*.18, body_w*.105)
        gap = key*.28
        gx = bx + body_w*.09
        gy = by + body_h*.36
        rects = {}
        for i in range(9):
            row, col = divmod(i, 3)
            rects[i+1] = QRectF(gx+col*(key+gap), gy+row*(key+gap), key, key)

        d = body_h*.34
        cx, cy = bx+body_w*.79, by+body_h*.59
        return QRectF(bx, by, body_w, body_h), QRectF(ox,oy,ow,oh), rects, QRectF(cx-d/2,cy-d/2,d,d)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        _, _, rects, enc = self._geometry()
        pos = event.position()
        for i, rect in rects.items():
            if rect.contains(pos):
                self._selected_key = i
                self._encoder_selected = False
                self.key_clicked.emit(i)
                self.update()
                return
        if enc.contains(pos):
            self._encoder_selected = True
            self.encoder_clicked.emit()
            self.update()
            return

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        body, oled, rects, enc = self._geometry()

        # soft floor shadow
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0,0,0,90))
        p.drawRoundedRect(body.translated(0, 8), 24, 24)

        # device chassis: layered 3D
        p.setBrush(QColor("#0b1017"))
        p.drawRoundedRect(body.adjusted(-2, 6, 2, 8), 24, 24)
        p.setBrush(QColor("#1a2230"))
        p.drawRoundedRect(body, 24, 24)
        p.setPen(QPen(QColor("#3c485c"), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(body, 24, 24)
        p.setPen(QPen(QColor("#0c121b"), 5))
        p.drawRoundedRect(body.adjusted(9,9,-9,-9), 17, 17)

        # OLED glass
        p.setPen(QPen(QColor("#46556c"), 1.5))
        p.setBrush(QColor("#05080d"))
        p.drawRoundedRect(oled, 8, 8)
        inner = oled.adjusted(4,4,-4,-4)
        p.setBrush(QColor("#07131c"))
        p.drawRoundedRect(inner, 5, 5)
        p.setPen(QColor("#8bb8ff"))
        if self._encoder_selected:
            oled_text = "ROTARY ENCODER"
        else:
            value = self._keys.get(self._selected_key, "")
            oled_text = value[5:] if value.startswith("TEXT:") else (value or f"KEY {self._selected_key}")
            oled_text = oled_text[:22]
        p.drawText(inner, Qt.AlignmentFlag.AlignCenter, oled_text)

        # keys
        for i, rect in rects.items():
            selected = (not self._encoder_selected and i == self._selected_key)
            pressed = (i == self._pressed_key and self._pulse > 0)

            # extruded bottom
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#070b10"))
            p.drawRoundedRect(rect.translated(0,5), 9, 9)

            if selected:
                fill = QColor("#4d8dff")
            elif pressed:
                fill = QColor("#6da5ff")
            elif self._keys.get(i):
                fill = QColor("#263c60")
            else:
                fill = QColor("#202a38")

            p.setBrush(fill)
            p.drawRoundedRect(rect, 9, 9)

            p.setPen(QPen(QColor("#6f7f95") if not selected else QColor("#a9c9ff"), 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(rect, 9, 9)

            # keycap highlight
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255,255,255,24))
            p.drawRoundedRect(rect.adjusted(5,4,-5,-rect.height()*.56), 5, 5)

            p.setPen(QColor("#ffffff"))
            f = QFont()
            f.setBold(True)
            f.setPointSize(max(9, int(rect.width()*.16)))
            p.setFont(f)
            p.drawText(rect.adjusted(0,-7,0,-rect.height()*.47), Qt.AlignmentFlag.AlignCenter, str(i))

            binding = self._keys.get(i, "")
            if binding:
                text = binding[5:] if binding.startswith("TEXT:") else binding
                text = text.replace("+", " + ")
                if len(text) > 12:
                    text = text[:11] + "…"
                f.setPointSize(max(6, int(rect.width()*.095)))
                f.setBold(False)
                p.setFont(f)
                p.setPen(QColor("#c8d9f5"))
                p.drawText(rect.adjusted(4, rect.height()*.30, -4, -6),
                           Qt.AlignmentFlag.AlignCenter, text)

        # encoder base and knob
        cx, cy = enc.center().x(), enc.center().y()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#070b10"))
        p.drawEllipse(enc.translated(0,6))
        p.setBrush(QColor("#303b4b"))
        p.drawEllipse(enc)
        p.setPen(QPen(QColor("#69788e"), 2))
        p.setBrush(QColor("#1b2431"))
        p.drawEllipse(enc.adjusted(5,5,-5,-5))

        if self._encoder_selected:
            p.setPen(QPen(QColor("#75a9ff"), 3))
            p.drawEllipse(enc.adjusted(-5,-5,5,5))

        p.setPen(QPen(QColor(ACCENT) if self._connected else QColor("#758297"), 4))
        p.drawLine(int(cx), int(enc.top()+enc.height()*.17), int(cx), int(enc.top()+enc.height()*.34))

        # tiny status LED
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#22c55e") if self._connected else QColor("#566275"))
        p.drawEllipse(int(body.right()-30), int(body.bottom()-29), 9, 9)

        p.end()


class KeyBindDialog(QDialog):
    def __init__(self, current_value, key_label, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Configure {key_label}")
        self.setMinimumWidth(410)
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel(f"{key_label}  •  Action")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        self.combo = QComboBox()
        self.combo.addItem("Custom shortcut")
        self.combo.addItems(COMMON_KEYS)
        layout.addWidget(self.combo)

        text_macro = current_value.startswith("TEXT:")
        self.edit = QLineEdit(current_value[5:] if text_macro else current_value)
        self.edit.setReadOnly(True)
        self.edit.setPlaceholderText("Press a shortcut, e.g. Ctrl+Shift+S")
        self.edit.installEventFilter(self)
        layout.addWidget(self.edit)

        self.text_mode = QCheckBox("Text macro")
        self.text_mode.setChecked(text_macro)
        self.text_mode.toggled.connect(self._set_text_mode)
        layout.addWidget(self.text_mode)

        self._captured_keys = {}
        self.combo.currentIndexChanged.connect(self._on_combo_changed)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_combo_changed(self, idx):
        if idx > 0:
            self.text_mode.setChecked(False)
            self.edit.setText(self.combo.currentText())

    def _set_text_mode(self, enabled):
        self.edit.setReadOnly(not enabled)
        self.edit.setPlaceholderText("Type text to send" if enabled else "Press a shortcut, e.g. Ctrl+Shift+S")

    def eventFilter(self, watched, event):
        if watched is self.edit and event.type() == QEvent.Type.KeyPress and not self.text_mode.isChecked():
            self._capture_key(event)
            return True
        if watched is self.edit and event.type() == QEvent.Type.KeyRelease and not self.text_mode.isChecked():
            return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event):
        if not self.text_mode.isChecked():
            self._capture_key(event)
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if not self.text_mode.isChecked():
            event.accept()
            return
        super().keyReleaseEvent(event)

    def _capture_key(self, event):
        if event.isAutoRepeat():
            return
        special = {
            Qt.Key.Key_Control:"CTRL", Qt.Key.Key_Shift:"SHIFT", Qt.Key.Key_Alt:"ALT",
            Qt.Key.Key_Meta:"GUI", Qt.Key.Key_Return:"ENTER", Qt.Key.Key_Enter:"ENTER",
            Qt.Key.Key_Tab:"TAB", Qt.Key.Key_Escape:"ESC", Qt.Key.Key_Space:"SPACE",
            Qt.Key.Key_Backspace:"BACKSPACE", Qt.Key.Key_Delete:"DELETE",
            Qt.Key.Key_Insert:"INSERT", Qt.Key.Key_Home:"HOME", Qt.Key.Key_End:"END",
            Qt.Key.Key_Left:"LEFT", Qt.Key.Key_Right:"RIGHT", Qt.Key.Key_Up:"UP",
            Qt.Key.Key_Down:"DOWN", Qt.Key.Key_Print:"PRTSC",
            Qt.Key.Key_CapsLock:"CAPSLOCK", Qt.Key.Key_NumLock:"NUMLOCK",
            Qt.Key.Key_PageUp:"PAGEUP", Qt.Key.Key_PageDown:"PAGEDOWN"
        }
        name = special.get(event.key())
        if name is None and Qt.Key.Key_F1 <= event.key() <= Qt.Key.Key_F24:
            name = f"F{event.key()-Qt.Key.Key_F1+1}"
        if name is None:
            text = event.text().strip()
            name = text.upper() if text.isalpha() else text
            if name == "+": name = "PLUS"
        if name:
            self._captured_keys[event.key()] = name
            modifiers = {"CTRL","SHIFT","ALT","GUI"}
            vals = list(self._captured_keys.values())
            vals = sorted(vals, key=lambda x: (x not in modifiers, vals.index(x)))
            self.edit.setText("+".join(vals))
            self.combo.setCurrentIndex(0)
            event.accept()

    def value(self):
        value = self.edit.text().strip()
        return f"TEXT:{value}" if self.text_mode.isChecked() else value.upper()



class AssignmentPanel(QFrame):
    """Right-side key assignment editor, with quick action tiles."""
    binding_changed = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("assignmentPanel")
        self._index = 1
        self._binding = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(18,18,18,18)
        root.setSpacing(12)
        self.setMinimumHeight(340)

        head = QHBoxLayout()
        icon = UiIcon("keyboard", size=40)
        icon.setObjectName("actionIcon")
        head.addWidget(icon)
        titles = QVBoxLayout()
        title = QLabel("Key assignment")
        title.setObjectName("panelTitle")
        sub = QLabel("Choose what this physical key should do")
        sub.setObjectName("panelSubtitle")
        titles.addWidget(title); titles.addWidget(sub)
        head.addLayout(titles); head.addStretch(1)
        root.addLayout(head)

        self.selected_label = QLabel("KEY 1")
        self.selected_label.setObjectName("selectionTitle")
        root.addWidget(self.selected_label)

        self.binding_label = QLabel("Unassigned")
        self.binding_label.setObjectName("assignmentPreview")
        self.binding_label.setWordWrap(True)
        root.addWidget(self.binding_label)

        grid = QGridLayout()
        grid.setSpacing(8)
        actions = [
            ("keyboard", "Shortcut"),
            ("text", "Text"),
            ("application", "Application"),
            ("system", "System"),
        ]
        for i,(ico,name) in enumerate(actions):
            b = QPushButton()
            b.setObjectName("actionTile")
            b.setMinimumHeight(52)
            tile_layout = QVBoxLayout(b)
            tile_layout.setContentsMargins(6, 5, 6, 5)
            tile_layout.setSpacing(3)
            tile_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tile_layout.addWidget(UiIcon(ico, b, 20), alignment=Qt.AlignmentFlag.AlignCenter)
            tile_layout.addWidget(QLabel(name, b), alignment=Qt.AlignmentFlag.AlignCenter)
            b.clicked.connect(lambda _=False, n=name: self._quick_action(n))
            grid.addWidget(b, i//2, i%2)
        root.addLayout(grid)

        self.configure_btn = QPushButton("Configure shortcut / text")
        self.configure_btn.setObjectName("primaryButton")
        self.configure_btn.clicked.connect(self._configure_requested)
        root.addWidget(self.configure_btn)

        self.clear_btn = QPushButton("Clear assignment")
        self.clear_btn.setObjectName("secondaryButton")
        self.clear_btn.setMinimumHeight(40)
        self.clear_btn.clicked.connect(lambda: self.binding_changed.emit(self._index, ""))
        root.addWidget(self.clear_btn)

        self._open_dialog_callback = None

    def set_dialog_callback(self, callback):
        self._open_dialog_callback = callback

    def set_selection(self, index, binding):
        self._index = index
        self._binding = binding or ""
        self.selected_label.setText(f"KEY {index}")
        self.binding_label.setText(
            self._binding[5:] if self._binding.startswith("TEXT:") else (self._binding or "Unassigned")
        )

    def _configure_requested(self):
        if self._open_dialog_callback:
            self._open_dialog_callback(self._index)

    def _quick_action(self, name):
        if name == "Text":
            value = "TEXT:"
        elif name == "Application":
            value = "APP:"
        elif name == "System":
            value = "SYSTEM:"
        else:
            value = self._binding
        if value != self._binding:
            self.binding_changed.emit(self._index, value)

class EncoderPanel(QFrame):
    """Clean visual encoder configurator with action selectors and sensitivity."""

    encoder_changed = Signal(str, str)
    sensitivity_changed = Signal(int)

    ACTIONS = [
        ("None", ""),
        ("Volume up", "VOLUME_UP"),
        ("Volume down", "VOLUME_DOWN"),
        ("Next track", "MEDIA_NEXT"),
        ("Previous track", "MEDIA_PREV"),
        ("Play / pause", "MEDIA_PLAY_PAUSE"),
        ("Brightness up", "BRIGHTNESS_UP"),
        ("Brightness down", "BRIGHTNESS_DOWN"),
        ("Scroll up", "SCROLL_UP"),
        ("Scroll down", "SCROLL_DOWN"),
        ("Horizontal scroll left", "HSCROLL_LEFT"),
        ("Horizontal scroll right", "HSCROLL_RIGHT"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("encoderCard")
        self.setMinimumHeight(560)
        root = QVBoxLayout(self)
        root.setContentsMargins(20,18,20,18)
        root.setSpacing(9)

        head = QHBoxLayout()
        icon = UiIcon("encoder", size=40)
        icon.setObjectName("encoderBigIcon")
        head.addWidget(icon)
        titles = QVBoxLayout()
        t = QLabel("Rotary encoder")
        t.setObjectName("panelTitle")
        st = QLabel("Configure rotation, press and sensitivity")
        st.setObjectName("panelSubtitle")
        titles.addWidget(t)
        titles.addWidget(st)
        head.addLayout(titles)
        head.addStretch(1)
        root.addLayout(head)

        sens = QFrame()
        sens.setObjectName("sensitivityCard")
        sl = QVBoxLayout(sens)
        sl.setContentsMargins(12, 8, 12, 8)
        top = QHBoxLayout()
        l = QLabel("Encoder sensitivity")
        l.setObjectName("encoderRowLabel")
        top.addWidget(l)
        top.addStretch(1)
        self.sens_label = QLabel("3")
        self.sens_label.setObjectName("sensPill")
        self.sens_label.setMinimumWidth(44)
        self.sens_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top.addWidget(self.sens_label)
        sl.addLayout(top)

        self.sens_slider = QSlider(Qt.Orientation.Horizontal)
        self.sens_slider.setMinimumHeight(28)
        self.sens_slider.setToolTip("More steps per detent sends more repeated actions")
        self.sens_slider.setRange(0, 10)
        self.sens_slider.setPageStep(1)
        self.sens_slider.setValue(3)
        self.sens_slider.valueChanged.connect(self._on_sens_changed)
        sl.addWidget(self.sens_slider)
        root.addWidget(sens)

        self.event_boxes = {}
        friendly = {
            "CW": ("clockwise", "Clockwise"),
            "CCW": ("counterclockwise", "Counter-clockwise"),
            "DOUBLE_PRESS": ("dot", "Double press"),
        }

        for event in ENCODER_EVENTS:
            row = QFrame()
            row.setObjectName("encoderRow")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(10,5,10,5)
            rl.setSpacing(10)

            ico, label = friendly.get(event, ("•", event))
            il = UiIcon(ico, row, 24)
            il.setObjectName("encoderRowIcon")
            rl.addWidget(il)

            lab = QLabel(label)
            lab.setObjectName("encoderRowLabel")
            lab.setMinimumWidth(130)
            rl.addWidget(lab)

            box = QComboBox()
            box.setEditable(False)
            for name, value in self.ACTIONS:
                box.addItem(name, value)
            box.currentIndexChanged.connect(lambda _i, e=event: self._emit_event(e))
            rl.addWidget(box, 1)

            self.event_boxes[event] = box
            root.addWidget(row)

        ticks = QHBoxLayout()
        for x in ("Precise", "Balanced", "Fast"):
            q = QLabel(x)
            q.setObjectName("tickLabel")
            ticks.addWidget(q)
        ticks.itemAt(1).widget().setAlignment(Qt.AlignmentFlag.AlignCenter)
        ticks.itemAt(2).widget().setAlignment(Qt.AlignmentFlag.AlignRight)
        sl.addLayout(ticks)

    def ensureVisible(self):
        self.scroll_to_self = True
        self.setFocus()
        self.update()

    def _emit_event(self, event):
        box = self.event_boxes[event]
        self.encoder_changed.emit(event, box.currentData() or "")

    def _on_sens_changed(self, value):
        self.sens_label.setText(str(value))
        self.sensitivity_changed.emit(value)

    def load_encoder(self, encoder, sensitivity):
        for event, box in self.event_boxes.items():
            value = encoder.get(event, "")
            idx = box.findData(value)
            box.blockSignals(True)
            box.setCurrentIndex(idx if idx >= 0 else box.findData("CUSTOM"))
            box.blockSignals(False)
        self.sens_slider.blockSignals(True)
        self.sens_slider.setValue(sensitivity)
        self.sens_label.setText(str(sensitivity))
        self.sens_slider.blockSignals(False)

    def current_encoder(self):
        return {e: b.currentData() or "" for e,b in self.event_boxes.items()}

    def current_sensitivity(self):
        return self.sens_slider.value()
