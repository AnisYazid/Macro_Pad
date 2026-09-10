"""
serial_link.py
---------------
Handles the USB/serial connection to the macro pad (Option B: HID keyboard
+ separate config interface). Runs the actual I/O on a background QThread
so the GUI never blocks, and emits Qt signals the UI can hook into.

If no device is found (or pyserial isn't happy with the port), the link
falls back to a SIMULATED mode so the app is still fully usable/testable
without hardware attached.
"""

import time
from PySide6.QtCore import QObject, QThread, Signal, Slot, QTimer

try:
    import serial
    import serial.tools.list_ports as list_ports
    PYSERIAL_AVAILABLE = True
except ImportError:
    PYSERIAL_AVAILABLE = False


DEVICE_VID_PID_HINTS = [
    # Common ESP32-S3 USB CDC VID:PID pairs (Espressif default + CP210x/CH340 boards).
    # Extend this list once you know the exact VID/PID your board enumerates as.
    (0x303A, 0x1001),  # Espressif USB JTAG/serial debug unit
    (0x303A, 0x8000),  # Espressif generic CDC
]

BAUD_RATE = 115200
FIRMWARE_INFO_TIMEOUT = 2.0


def find_candidate_ports():
    """Return a list of available serial ports."""
    if not PYSERIAL_AVAILABLE:
        return []
    ports = []
    for p in list_ports.comports():
        ports.append((p.device, p.description or "Unknown device"))
    return ports


class SerialWorker(QObject):
    """Runs on a background thread; owns the actual serial.Serial object."""

    connected = Signal(str, str)       # port, firmware_version
    disconnected = Signal()
    error = Signal(str)
    command_result = Signal(str, bool, str)  # command, success, raw_reply
    encoder_event = Signal(str)
    log = Signal(str)

    def __init__(self):
        super().__init__()
        self._ser = None
        self._port_name = None
        self.simulated = False
        self._poll_timer = None

    # --- connection lifecycle -------------------------------------------------
    @Slot(str)
    def connect_to(self, port_name: str):
        if not PYSERIAL_AVAILABLE or port_name in (None, "", "SIM"):
            self._start_simulation(port_name or "SIM")
            return

        try:
            self._ser = serial.Serial(port_name, BAUD_RATE, timeout=1)
            time.sleep(0.2)  # let the board settle after DTR toggle
            self._port_name = port_name
            self.simulated = False
            self._poll_timer = QTimer(self)
            self._poll_timer.setInterval(20)
            self._poll_timer.timeout.connect(self._poll_serial)
            self._poll_timer.start()
            firmware = self._request_firmware_info()
            self.log.emit(f"Connected to {port_name}")
            self.connected.emit(port_name, firmware or "unknown")
        except Exception as exc:  # noqa: BLE001 - surface any serial error to UI
            self.log.emit(f"Failed to open {port_name}: {exc}")
            self.error.emit(str(exc))

    def _start_simulation(self, label: str):
        self.simulated = True
        self._port_name = label
        self.log.emit("pyserial not available or no hardware found - running in SIMULATED mode")
        self.connected.emit(label, "SIM-1.0.0")

    def simulate_encoder_press(self):
        self.encoder_event.emit("PRESS")

    @Slot()
    def disconnect(self):
        if self._poll_timer:
            self._poll_timer.stop()
        if self._ser and self._ser.is_open:
            self._ser.close()
        self._ser = None
        self.simulated = False
        self.disconnected.emit()
        self.log.emit("Disconnected")

    def _request_firmware_info(self):
        reply = self._send_raw("GET_INFO")
        # Expected reply format: "INFO,<model>,<firmware_version>"
        if reply and reply.startswith("INFO,"):
            parts = reply.split(",")
            if len(parts) >= 3:
                return parts[2]
        return None

    # --- sending commands -------------------------------------------------
    @Slot(str)
    def send_command(self, cmd: str):
        if self.simulated:
            time.sleep(0.02)
            self.log.emit(f"[SIM] {cmd} -> OK")
            self.command_result.emit(cmd, True, "OK")
            return

        reply = self._send_raw(cmd)
        ok = bool(reply) and reply.startswith("OK")
        self.command_result.emit(cmd, ok, reply or "")
        self.log.emit(f"{cmd} -> {reply}")

    def _send_raw(self, cmd: str):
        if not self._ser or not self._ser.is_open:
            self.error.emit("Not connected")
            return None
        try:
            self._ser.write((cmd + "\n").encode("utf-8"))
            self._ser.flush()
            deadline = time.time() + FIRMWARE_INFO_TIMEOUT
            while time.time() < deadline:
                line = self._ser.readline().decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                if line.startswith("EVENT,"):
                    self.encoder_event.emit(line[6:])
                    continue
                return line
            return None
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))
            return None

    @Slot()
    def _poll_serial(self):
        if not self._ser or not self._ser.is_open:
            return
        try:
            while self._ser.in_waiting:
                line = self._ser.readline().decode("utf-8", errors="replace").strip()
                if line.startswith("EVENT,"):
                    self.encoder_event.emit(line[6:])
                elif line:
                    self.log.emit(f"Device -> {line}")
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


class SerialLink(QObject):
    """
    Thin façade used by the GUI. Owns a QThread running SerialWorker and
    forwards calls/signals across the thread boundary.
    """

    connected = Signal(str, str)
    disconnected = Signal()
    error = Signal(str)
    command_result = Signal(str, bool, str)
    encoder_event = Signal(str)
    log = Signal(str)

    def __init__(self):
        super().__init__()
        self._thread = QThread()
        self.worker = SerialWorker()
        self.worker.moveToThread(self._thread)
        self._thread.start()

        # forward signals
        self.worker.connected.connect(self.connected)
        self.worker.disconnected.connect(self.disconnected)
        self.worker.error.connect(self.error)
        self.worker.command_result.connect(self.command_result)
        self.worker.encoder_event.connect(self.encoder_event)
        self.worker.log.connect(self.log)

    def connect_to(self, port_name: str):
        # invoke on worker thread
        from PySide6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self.worker, "connect_to", Qt.QueuedConnection, Q_ARG(str, port_name)
        )

    def disconnect(self):
        from PySide6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(self.worker, "disconnect", Qt.QueuedConnection)

    def send_command(self, cmd: str):
        from PySide6.QtCore import QMetaObject, Qt, Q_ARG
        QMetaObject.invokeMethod(
            self.worker, "send_command", Qt.QueuedConnection, Q_ARG(str, cmd)
        )

    def shutdown(self):
        self._thread.quit()
        self._thread.wait(1000)
