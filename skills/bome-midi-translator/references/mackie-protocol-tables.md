# Mackie MCU / HUI protocol tables

Quick reference to map controllers to any mixer, audio interface or DAW that supports Mackie control surfaces.

## 1. MCU (Mackie Control Universal) — full mapping

### 1.1 Faders (8 channels + Master)

| Element | MIDI |
|---|---|
| Fader bus 1 | Pitch Bend ch1: `E0 LSB MSB` |
| Fader bus 2 | Pitch Bend ch2: `E1 LSB MSB` |
| ... | ... |
| Fader bus 8 | Pitch Bend ch8: `E7 LSB MSB` |
| Master fader | Pitch Bend ch9: `E8 LSB MSB` |

14-bit value: `value = (MSB << 7) | LSB`, range 0..16383.

### 1.2 V-Pots (rotary encoders) — always ch1

| Element | MIDI |
|---|---|
| V-Pot 1 rotate | CC ch1 `0x10` (16) |
| V-Pot 2 rotate | CC ch1 `0x11` (17) |
| ... | ... |
| V-Pot 8 rotate | CC ch1 `0x17` (23) |
| V-Pot 1 press | Note ch1 `0x20` (32) vel 127 |
| ... | ... |
| V-Pot 8 press | Note ch1 `0x27` (39) vel 127 |

**Rotation encoding** (signed relative):
```
bit 6 = direction (0 = CW, 1 = CCW)
bits 0-5 = magnitude (1..63)
delta = magnitude * (bit6 ? -1 : +1)
```

### 1.3 Buttons (Notes ch1)

| Zone | Note range | Detail |
|---|---|---|
| Solo bus | `0x08`..`0x0F` | bus 1..8 |
| Mute bus | `0x10`..`0x17` | bus 1..8 |
| Select ch | `0x18`..`0x1F` | bus 1..8 |
| V-Pot press | `0x20`..`0x27` | bus 1..8 |
| Rec arm | `0x00`..`0x07` | bus 1..8 |
| Function F1..F8 | `0x36`..`0x3D` | — |
| Bank left/right | `0x2E` / `0x2F` | — |
| Channel left/right | `0x30` / `0x31` | — |
| Flip | `0x32` | — |
| Global view | `0x33` | — |
| Name/Value | `0x34` | — |
| SMPTE/Beats | `0x35` | — |
| Modify (Shift/Option/Ctrl/Alt) | `0x46`..`0x49` | — |
| Auto Read/Write/Touch/Latch | `0x4A`..`0x4D` | — |
| Save | `0x50` | — |
| Undo | `0x51` | — |
| Cancel | `0x52` | — |
| Enter | `0x53` | — |
| Marker/Nudge/Cycle/Drop/Replace/Click/Solo | `0x54`..`0x5A` | — |
| Rewind | `0x5B` | — |
| Fast Forward | `0x5C` | — |
| Stop | `0x5D` | — |
| Play | `0x5E` | — |
| Record | `0x5F` | — |
| Cursor Up/Down/Left/Right | `0x60`..`0x63` | — |
| Scrub | `0x64` | — |
| User switches A/B | `0x66`..`0x67` | — |
| Fader touch ch1..8 | `0x68`..`0x6F` | vel 127 = touch, 0 = release |
| Master fader touch | `0x70` | — |
| SMPTE LED | `0x71` | — |
| Beats LED | `0x72` | — |
| RUDE Solo LED | `0x73` | — |
| Relay click | `0x76` | — |

**Velocity**: 127 = press, 0 = release. For LED feedback the host sends vel 127 = LED on, 0 = LED off.

### 1.4 Jog Wheel

CC ch1 `0x3C` (60) — signed relative, same format as V-Pot.

### 1.5 LCD Display (SysEx)

```
F0 00 00 66 14 12 <offset> <ascii_chars...> F7
```

Writes text to the MCU LCD. Offset 0..111 (2 lines of 56). Rarely used outside real MCU hardware.

### 1.6 Timecode Display (SysEx)

```
F0 00 00 66 14 11 <pos> <char> F7
```

### 1.7 Meters

```
F0 00 00 66 14 20 <channel> <level> F7
```

Channel 0..7, level 0x00..0x0F (0 = silence, F = clip).

---

## 2. HUI (Human User Interface)

### 2.1 Heartbeat

| Direction | Message | Rate |
|---|---|---|
| Host → Controller | `90 00 00` (Note On ch1 note=0 vel=0) | every ~2 s |
| Controller → Host | identical echo | every ~2 s |

If silent for > 5 s → controller considered offline, re-pairs. **Mandatory**.

In Bome: `<Simple Type="HUI"><Value1 num="0"/></Simple>` (native type).

### 2.2 Zone/Port architecture

HUI is stateful: to change an element, you **first select the zone** (the control), then send the **value on the matching port**.

```
CC ch1 0x0F val=ZONE_ID        ← select zone
CC ch1 0x2F val=PORT_ID|FLAG   ← select port + flag (touch/release/move)
```

The pair is atomic: send **both**, in order.

### 2.3 HUI faders

| Step | MIDI |
|---|---|
| Select fader zone X (X=0..7) | `B0 0F (0x00..0x07)` |
| Fader MSB | `B0 (zone+0x00) <MSB>` |
| Select LSB port | `B0 0F (0x00..0x07)` |
| Fader LSB | `B0 (zone+0x20) <LSB>` |

More compact (encoding seen in Bome): pair `B0 0F pp` + `B0 2F qq` where:
- `pp` (zone) bit 6 set = state (touch/move/release)
- `qq` (port) = value byte

Touch/Move/Release flags:
- `0x40` = touch (start)
- `0x20` = move (continuous)
- `0x00` = release (end)

### 2.4 HUI V-Pots

Same as MCU: CC ch1 `0x10..0x17`, signed relative encoding.

### 2.5 HUI buttons

Select the zone, then the port with a flag:
```
B0 0F <zone>
B0 2C <port>       ← LED off / press
B0 2C <port|0x40>  ← LED on
```

### 2.6 HUI LCD

```
F0 00 00 66 05 00 11 <data_4chars_per_strip> ... F7
```

Strip = channel, 4 chars × 8 strips × 2 lines.

### 2.7 Main HUI zones

| Zone | Control |
|---|---|
| `0x00`..`0x07` | Faders 1..8 |
| `0x08` | Keyboard shortcuts |
| `0x09` | Window |
| `0x0A` | Channel select / Assign |
| `0x0B`..`0x17` | (varies) |
| `0x18`..`0x1F` | V-Sel buttons |
| Etc. | see the Mackie/Digidesign HUI spec |

---

## 3. MCU vs HUI at a glance

| Aspect | MCU | HUI |
|---|---|---|
| Faders | Pitch Bend (simple 14-bit) | stateful CC pairs (zone/port) |
| Heartbeat | not required | **mandatory, ~2 s** |
| Encoding | direct | indirect (select first) |
| Bytes per fader event | 3 | 6 (2 × 3-byte messages) |
| Latency | slightly lower | OK |
| Adoption | modern DAWs (Ableton, Logic, Cubase MCU mode), many audio-interface mixers | Pro Tools native |
| Complexity in Bome | low | high (zone handling) |

**Rule of thumb**: if the target supports both, use MCU.

---

## 4. Typical setup: Bome in front of an MCU-capable mixer

Many software mixers (audio-interface control apps, DAWs) accept an MCU surface on a configurable MIDI port.

| Mixer element | MCU |
|---|---|
| Mix bus fader 1..8 | Pitch Bend ch1..8 |
| Bus mute | Note ch1 `0x10..0x17` toggle |
| Bus solo | Note ch1 `0x08..0x0F` |
| Channel select | Note ch1 `0x18..0x1F` |
| EQ band gain (after select) | V-Pot via CC `0x10..0x17` |
| Snapshot recall | Program Change ch1 (0..127) |
| Bank prev/next | Note `0x2E`/`0x2F` (banks of 8) |

### 4.1 Wiring

```
Mixer → Control Surfaces → Add surface: Mackie Control
      → Input port  : IAC "Mixer-In"  (from Bome)
      → Output port : IAC "Mixer-Out" (to Bome, LED feedback)
```

### 4.2 Available feedback

The mixer usually sends back on its output port:
- Note ch1 vel 127/0 on mute/solo notes = bus state
- Pitch Bend ch1..8 = fader position after an external touch
- V-Pot LED ring CC (rare)

Bome can listen on that port and remap to your controller's LEDs.

---

## 5. Sources

- Mackie Control Universal MIDI Protocol Specification (Mackie)
- HUI protocol documentation (Digidesign/Avid, community specs)
- Bome forum thread "HUI implementation": forum.bome.com
