#!/usr/bin/env python3
"""
NISSOU Macro Pad Configurator
------------------------------
Entry point. Run with:

    python main.py

Requires: PySide6, pyserial (see requirements.txt)
"""

import sys
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


APP_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #10141b;
    color: #e8edf5;
    font-family: "Segoe UI";
    font-size: 13px;
}
QMainWindow { border: none; }
QFrame#sidebar {
    background-color: #171c25;
    border-right: 1px solid #293241;
}
QFrame#connectionCard, QFrame#card, QGroupBox {
    background-color: #1a202b;
    border: 1px solid #303b4b;
    border-radius: 12px;
    color: #e8edf5;
}
QLabel#brandTitle, QLabel#profileTitle {
    color: #f3f6fb;
    font-weight: 700;
}
QLabel#brandSubtitle { color: #8d99aa; letter-spacing: 1px; }
QLabel#statusLabel { color: #b8c2d0; }
QLabel#selectedKeyTitle {
    color: #f3f6fb;
    font-size: 20px;
    font-weight: 700;
}
QLabel#assignmentValue {
    background-color: #141a23;
    border: 1px solid #303b4b;
    border-radius: 8px;
    color: #dce7f7;
    padding: 12px;
    min-height: 42px;
}
QListWidget#profileList {
    background-color: transparent;
    border: none;
    outline: none;
}
QListWidget#profileList::item {
    background-color: #202733;
    border: 1px solid #303b4b;
    border-radius: 8px;
    color: #dce4ef;
    padding: 10px;
    margin: 2px 0;
}
QListWidget#profileList::item:hover {
    border-color: #5b91ed;
}
QListWidget#profileList::item:selected {
    background-color: #263f6b;
    border-color: #5790f4;
    color: #ffffff;
}
QScrollArea#contentScroll, QWidget#contentArea { background-color: #10141b; }
QLabel#sectionLabel, QGroupBox::title {
    color: #9eabba;
    font-weight: 600;
}
QPushButton {
    background-color: #232b38;
    border: 1px solid #3a4658;
    border-radius: 8px;
    color: #e8edf5;
    padding: 8px 12px;
}
QPushButton:hover {
    background-color: #2b3e5e;
    border-color: #5790f4;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #1e3151;
    border-color: #6da0ff;
}
QPushButton:disabled {
    background-color: #1b212b;
    color: #687588;
    border-color: #2b3442;
}
QPushButton#primaryButton {
    background-color: #3d7bf7;
    border-color: #3d7bf7;
    color: #ffffff;
    font-weight: 600;
}
QPushButton#primaryButton:hover {
    background-color: #5790f4;
    border-color: #5790f4;
}
QPushButton#primaryButton:disabled {
    background-color: #304a7d;
    border-color: #304a7d;
    color: #aebedc;
}
QPushButton#dangerButton:hover {
    background-color: #4b252c;
    border-color: #d9534f;
    color: #ffb7b7;
}
QComboBox, QLineEdit, QPlainTextEdit {
    background-color: #141a23;
    border: 1px solid #3a4658;
    border-radius: 7px;
    color: #e8edf5;
    padding: 7px;
}
QComboBox:hover, QLineEdit:focus, QPlainTextEdit:focus {
    border-color: #5790f4;
}
QComboBox QAbstractItemView {
    background-color: #1a202b;
    color: #e8edf5;
    selection-background-color: #2d4f86;
    selection-color: #ffffff;
}
QSlider::groove:horizontal {
    height: 8px;
    background: #354154;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 22px;
    margin: -8px 0;
    border-radius: 8px;
    background: #3d7bf7;
}
QLabel#sensPill {
    background-color: #263f6b;
    color: #bcd3ff;
    border-radius: 9px;
    font-weight: 700;
    font-size: 15px;
    padding: 5px 7px;
}
QLabel#dialogHint { color: #aab5c4; }
QSplitter::handle { background-color: #293241; }
QSplitter#editorSplitter::handle { background-color: #3a4658; }
QPlainTextEdit#logView {
    background-color: #0d1117;
    color: #b9c8dc;
    border-color: #303b4b;
}
QToolButton {
    background-color: transparent;
    border: none;
    color: #78a8ff;
    font-weight: 600;
}
QToolButton:hover { color: #ffffff; }

QFrame#deviceCard, QFrame#actionCard, QFrame#assignmentPanel, QFrame#encoderCard {
    background-color: #171d28;
    border: 1px solid #2e3949;
    border-radius: 16px;
}
QLabel#sectionTitle {
    color: #f4f7fb;
    font-size: 16px;
    font-weight: 700;
}
QLabel#mutedLabel, QLabel#panelSubtitle, QLabel#tickLabel {
    color: #8995a7;
}
QLabel#selectionTitle {
    color: #f5f7fb;
    font-size: 19px;
    font-weight: 800;
    letter-spacing: 1px;
}
QLabel#panelTitle {
    color: #f5f7fb;
    font-size: 15px;
    font-weight: 700;
}
QWidget#actionIcon, QWidget#encoderBigIcon {
    background-color: #253754;
    color: #8eb9ff;
    border-radius: 10px;
    font-size: 22px;
    font-weight: 700;
    min-width: 40px;
    max-width: 40px;
    min-height: 40px;
    max-height: 40px;
    qproperty-alignment: AlignCenter;
}
QLabel#assignmentPreview {
    background-color: #10161f;
    border: 1px solid #334154;
    border-radius: 11px;
    color: #dce8fa;
    padding: 14px;
    font-size: 16px;
    font-weight: 650;
    min-height: 36px;
}
QPushButton#actionTile {
    background-color: #202a38;
    border: 1px solid #344257;
    border-radius: 11px;
    color: #dbe5f3;
    font-weight: 650;
    padding: 9px;
}
QPushButton#actionTile:hover {
    background-color: #293c5b;
    border-color: #5b91ed;
}
QPushButton#secondaryButton {
    background-color: #1b222d;
    border-color: #344052;
}
QFrame#encoderRow {
    background-color: #111821;
    border: 1px solid #2d394a;
    border-radius: 11px;
}
QWidget#deviceSurface {
    background-color: #111821;
    border: 1px solid #2d394a;
    border-radius: 14px;
}
QSplitter#editorSplitter::handle {
    background-color: #3a4658;
}
QWidget#encoderRowIcon {
    color: #76a8ff;
    font-size: 19px;
    font-weight: 700;
    qproperty-alignment: AlignCenter;
}
QLabel#encoderRowLabel {
    color: #dce5f2;
    font-weight: 600;
}
QFrame#sensitivityCard {
    background-color: #111821;
    border: 1px solid #2d394a;
    border-radius: 11px;
}
QPushButton#appChip {
    background-color: #171f2b;
    border: 1px solid #303c4e;
    border-radius: 11px;
    padding: 3px;
    text-align: left;
}
QPushButton#appChip:hover {
    background-color: #202d40;
    border-color: #5b91ed;
}
QLabel#appChipTitle {
    color: #edf2f8;
    font-weight: 650;
}
QLabel#appChipSub {
    color: #7f8da0;
    font-size: 10px;
}
QLabel#dialogTitle {
    color: #f5f7fb;
    font-size: 17px;
    font-weight: 700;
}
"""


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NISSOU Macro Pad Configurator")
    app.setApplicationDisplayName("NISSOU Macro Pad")
    app.setStyleSheet(APP_STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
