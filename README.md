# NISSOU 3×3 Macro Pad

A compact, programmable **3×3 mechanical macro pad** built around the **Arduino Pro Micro (ATmega32U4)**, featuring an **EC11 rotary encoder**, **0.91" I²C OLED display**, and a dedicated PC configurator.

The project is designed as a foundation for a future commercial macro-pad product under **NISSOU / OptiBot DZ**, with support planned for customizable profiles, application-specific macros, encoder actions, and graphical configuration software.

---

## ✨ Features

- 🔲 3×3 mechanical key layout
- 🎛️ EC11 rotary encoder with push button
- 🖥️ 0.91" I²C OLED display
- 🔌 USB connection
- ⌨️ Native USB HID using ATmega32U4
- 💾 Configurable macro profiles
- 🎮 Application-specific profiles
- 🔊 Volume and media control through rotary encoder
- ⚙️ Adjustable encoder sensitivity
- 🖱️ Click-to-configure physical device interface
- 💻 Windows configurator software
- 🎨 Modern 3D-style device visualization
- 🚫 No RGB lighting in the current version
- 🔮 Future wireless/BLE version planned

---

# 🧩 Hardware

### Main Controller

**Arduino Pro Micro — ATmega32U4**

The Pro Micro was selected for the first prototype because the ATmega32U4 provides native USB HID functionality, allowing the macro pad to be recognized by a computer as a keyboard.

### Components

| Component | Quantity |
|---|---:|
| Arduino Pro Micro | 1 |
| Mechanical switches | 9 |
| EC11 rotary encoder module | 1 |
| 0.91" I²C OLED | 1 |
| Keycaps | 9 |
| USB cable | 1 |
| 3D-printed enclosure | Optional |

---

# 🔌 Pinout

## OLED — I²C

The OLED uses the Pro Micro's I²C interface.

| OLED | Pro Micro |
|---|---|
| VCC | VCC |
| GND | GND |
| SDA | D2 |
| SCL | D3 |

```text
OLED
 ┌─────────────┐
 │ VCC ────────┼── VCC
 │ GND ────────┼── GND
 │ SDA ────────┼── D2
 │ SCL ────────┼── D3
 └─────────────┘
