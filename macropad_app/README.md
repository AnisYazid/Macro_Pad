# NISSOU Macro Pad Configurator

A PySide6 desktop app for configuring a 3×3 macro pad + rotary encoder
 built on a Pro Micro, following the USB HID + serial configuration architecture:
enumerates as a USB HID keyboard *and* exposes a separate USB CDC serial
config interface that this app talks to.

## Running it

```bash
pip install -r requirements.txt
python main.py
```

No hardware needed to try it — if no serial device is found (or you pick
"SIMULATED" from the device dropdown), the app runs in a simulated mode
so you can build/test profiles fully offline.

## What's included

- **3×3 key grid** — click any key to assign a combo (dropdown of common
  combos + free-text entry, e.g. `CTRL+SHIFT+R`).
- **Encoder panel** — assign actions to CW / CCW / press / double-press /
  hold+rotate, plus a sensitivity slider (1–10 steps per detent).
- **Profiles** — New / Rename / Delete, stored as JSON under
  `~/.config/NissouMacroPad/profiles/` (or `%APPDATA%` on Windows).
  Ships with three starter profiles: Gaming, OBS Streaming, General.
- **Device connection bar** — lists serial ports (via `pyserial`),
  connect/disconnect, and shows firmware version once connected.
- **Push to Macro Pad** — sends the full profile to the device using the
  line protocol below, then a `SAVE` so it persists in flash.
- **Device log** — raw command/response trace at the bottom of the window.

## Pro Micro wiring

The firmware uses the analog pins as digital GPIOs, so the encoder does not
consume D4, D5, or D6:

```
EC11 GND  -> Pro Micro GND
EC11 S1   -> A2
EC11 S2   -> A1
EC11 KEY  -> A0
EC11 5V   -> Pro Micro VCC
```

For the 0.91-inch 128x32 I2C SSD1306 OLED:

```
OLED GND  -> GND
OLED VCC  -> VCC
OLED SDA  -> D2 (SDA)
OLED SCL  -> D3 (SCL)
```

Install `Adafruit GFX Library`, `Adafruit SSD1306`, and `HID-Project` in the
Arduino IDE before compiling `firmware/macropad_firmware.ino`. The firmware expects the
OLED at I2C address `0x3C`; change `OLED_ADDRESS` if the display uses `0x3D`.

## Serial protocol (what the ESP32-S3 firmware needs to implement)

Plain-text, one command per line, `\n`-terminated, 115200 baud. Firmware
replies with `OK` or `ERR,<reason>` on its own line (one reply per command).

```
SET_KEY,<1-9>,<COMBO>          e.g. SET_KEY,1,CTRL+C
SET_ENCODER,<EVENT>,<ACTION>   EVENT: CW | CCW | PRESS | DOUBLE_PRESS | HOLD_CW | HOLD_CCW
SET_SENSITIVITY,<0-10>         sensitivity level; firmware scales this to 2-40 actions per detent
SET_PROFILE_NAME,<name>
SAVE                           persist current config to flash
GET_INFO                       firmware replies: INFO,<model>,<firmware_version>
```

`NONE` is sent for any key/encoder slot left unassigned.

### Suggested firmware-side flow
1. On boot, load the last-saved profile from flash (or a default) and
   apply it to the HID keyboard task.
2. Run the CDC serial task in parallel, listening for the commands above.
3. Buffer incoming `SET_*` commands into a working config struct; only
   write to flash on `SAVE`, to avoid wearing it out during editing.
4. Keep the HID task running throughout — the config interface and the
   keyboard emulation should never block each other.

## Project layout

```
main.py                  - entry point, dark theme stylesheet
app/
  protocol.py             - Profile dataclass + command builders
  serial_link.py           - QThread-backed serial I/O, simulated fallback
  profile_store.py         - JSON profile persistence + starter profiles
  widgets.py                - KeyGrid, KeyButton, EncoderPanel
  main_window.py            - assembles everything into the main window
requirements.txt
```

## Packaging as a Windows .exe (later)

Once you're happy with it:

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name MacroPad main.py
```

## Extending

- **Firmware auto-update**: add `CHECK_UPDATE` / `PUSH_FIRMWARE` commands
  and a small panel next to the device log — the log/connection
  infrastructure here already supports adding more command types easily.
- **Live key capture**: swap `KeyBindDialog`'s text entry for an actual
  `keyPressEvent` capture if you want "press the key you want" UX instead
  of typing `CTRL+SHIFT+R`.
- **Binary protocol**: if the text protocol above ever becomes a
  bottleneck, `serial_link.py` is the only place that needs to change —
  the rest of the app just calls `send_command(str)`.
