---
name: bome-midi-translator
description: Syntax and architecture reference for Bome MIDI Translator Pro (BMTP). Rules, variables, actions (MIDI/Timer/Perform/Keystroke/VarStorage), the `.bmtp` file format, Mackie MCU/HUI conventions, common patterns (14-bit fader, relative V-Pot, banking, HUI heartbeat). Use whenever the topic is Bome, BomeBox, MT Pro, a `.bmtp` file, a translator, a Bome preset, Mackie HUI/MCU, or converting between different MIDI message types.
---

# Bome MIDI Translator Pro — Complete Reference

## When to use this skill

Anything involving:
- `.bmtp` files (creating, editing, parsing, debugging)
- Bome rules (local/global variables, operators, conditionals)
- Bome actions: MIDI / Timer / Perform / Keystroke / Preset / Project / Variable Storage / Mouse / AppleScript / Serial / Execute File
- BomeBox (hardware) and MT Player
- MIDI conversions: CC → Pitch Bend, NRPN, SysEx, MPE
- Mackie protocols: **MCU** (Mackie Control Universal) and **HUI** (incl. ping, 14-bit CC pairs, V-Pot)
- Banking, snapshots, LED feedback, relative encoders

---

## 1. Concepts

```
Project
├── MIDI Ports / Aliases (USB, virtual, IAC, Bonjour)
├── MIDI Router (rule-free MIDI thru)
└── Preset 0, Preset 1, ... Preset N
    ├── Default In/Out Ports (inherited)
    ├── Active / Inactive
    └── Translator Entry 0, 1, 2, ...
        ├── Incoming Action (1 trigger)
        ├── Rules (compiled stack-machine program)
        └── Outgoing Action (1 or more)
```

**Key concept**: 1 translator = 1 incoming → rules → 1 outgoing. For several outgoing actions, either tick **"Multiple Actions"**, or fire a `Perform` that wakes up N translators sharing the same Perform name.

**Matching order**: for an incoming event, Bome tests every translator (active preset, matching port) **in order of appearance**. Every match runs its rules. If `Swallow` is ticked on the incoming action, the MIDI Router does not pass the original message through.

---

## 2. Rules — Language

### 2.1 Variable types

| Type | Notation | Lifetime | Init |
|---|---|---|---|
| **Local** | doubled letters: `oo pp qq rr ss tt uu vv ww xx` | current incoming event only, isolated per thread | **not initialized** — reading before writing = random |
| **Global** | 2 chars, first in `g..z`, except the local doubles: `ga-gz g0-g9 ha-hz ... za-z9`, **plus** `oa-x9` (1.9.0+) | whole project session | 0 at startup |
| **Persistent** | any global loaded/saved through a `Variable Storage` action | survives between sessions | depends on the file |

**Valid examples**: `pp`, `qq`, `ga`, `h4`, `kd`, `j0`, `nb`, `zg`, `oa`, `x9`.
**Invalid**: `aa` (prefix `a` is not global), `op` (different letters for a local), `g00` (3 chars).

Range: signed 32-bit integer. Wraps at ±2 147 483 647. No floats.

### 2.2 Rule types

| Type | Syntax | Notes |
|---|---|---|
| **Assignment** | `pp = 20`, `ga = qq` | direct assignment |
| **Expression** | `pp = a OP b` | arithmetic/bitwise, **2 operands max** per line |
| **Conditional** | `if A OP B then <action>` | action = Assignment, Expression, Goto, Perform, Log, Skip 1, Skip 2, Exit-execute, Exit-skip |
| **Else** | `else <action>` | since 1.9.1, chainable with `else if` |
| **Goto** | `goto label` | beware of infinite loops |
| **Label** | `label name` | Goto target |
| **Perform** | `Perform "name", p1, p2` | fires an internal event immediately |
| **Log** | `Log "text %pp%"` | `%var%` format, `%02x var` for hex |
| **Exit-Execute** | `exit rules, execute outgoing` | stop + fire outgoing |
| **Exit-Ignore** | `exit rules, skip outgoing` | stop + skip outgoing |

### 2.3 Operators

| Category | Operator | Semantics |
|---|---|---|
| Arithmetic | `+ - * / %` | divide = integer truncation, modulo undefined if 0 |
| Bitwise | `& \| ^ >> <<` | 32-bit signed, shift right fills with 0 (logical, not arithmetic) |
| Compare (if) | `== != >= <= > <` | only operators allowed in conditionals |

**Critical syntax limit**: an expression has only **2 operands**. No `pp = a + b + c`. Split into lines:
```
pp = a + b
pp = pp + c
```

### 2.4 Log format

```
Log "Fader %pp% touched"          // decimal
Log "Note 0x%02x velocity %qq%"   // hex, at least 2 digits
Log "Bank %ga%"                   // global var
```

### 2.5 Number literals

- Decimal: `127`
- Hex: `0x7F` (prefix `0x`, lower or upper case)
- No binary or octal.

### 2.6 Rule best practices

1. Always **initialize a local** in the incoming action or the first rule, otherwise behaviour is random.
2. Prefer **Perform** over a 0 ms timer to chain several outgoing actions.
3. **One global variable per persistent state**, not one per intermediate value (use locals).
4. Use `if (...) skip` instead of nesting — Bome has no `{ }` blocks.
5. **No preset scope**: all globals are project-wide.
6. `noexecute` is the compiled keyword for Exit-skip.

---

## 3. Actions

### 3.1 MIDI Message

**Simple mode** (Capture MIDI): Bome detects the type (Note On, CC, PC, Pitch Bend, mono/poly AT, MPE).

**Raw mode** (recommended for Mackie/HUI/SysEx): hex string with embedded variables.

| Raw string | Meaning |
|---|---|
| `9F 6F pp` | Note On ch16, note 0x6F, velocity → `pp` |
| `B4 xx pp` | CC ch5, CC number → `xx`, value → `pp` |
| `BA ww 7F` | CC ch11, number = `ww`, value = exactly 127 |
| `C4 nn` | Program Change ch5, number → `nn` |
| `pp qq rr` | any 3-byte message |
| `F0 7F 7F 04 01 pp qq F7` | SysEx Master Volume, `pp`=LSB, `qq`=MSB |
| `E0 qq pp` | Pitch Bend ch1, LSB=`qq`, MSB=`pp` |

**14-bit Pitch Bend (Mackie)**:
```
qq = val_LSB         // 0..127
pp = val_MSB         // 0..127
// full 14-bit: combined = (pp << 7) | qq
// 7-bit CC fader (0..127) → 14-bit:
bend = cc_val * 128
qq = bend & 0x7F
pp = bend >> 7
```

The outgoing action can target several ports: set `Specific Ports` on the translator, or inherit from the preset.

### 3.2 Timer

| Field | Notes |
|---|---|
| **Name** | identifier, matched by the Incoming Timer |
| **Once / Multiple / Infinite** | infinite = only stoppable with Kill Timer |
| **Initial Duration (ms)** | delay before the first tick |
| **Repeat Duration (ms)** | spacing between later ticks |
| **Repeat Count** | ignored unless Multiple |
| **Parameters** | up to 10, comma-separated (vars or numbers), evaluated at activation |
| **Counter var** | incremented on each tick (0, 1, 2, ...) |

Retrigger: starting a timer with the same name **resets** its counter and timer (no stacking).

**HUI heartbeat pattern**: infinite 1000 ms timer sending the HUI ping:
```
Incoming Trigger : Tim "PingHUI"
Outgoing MIDI    : Simple Type="HUI" Value1="0"   // native Bome HUI handshake type
Activation Init  : Tim Activate "PingHUI" Once 0:0:1000 Infinite
```
(For MCU this is **not needed**: MCU has no mandatory heartbeat.)

### 3.3 Perform

Synchronous; immediately fires every translator with the same `Incoming Perform` name.

```
Outgoing : Perform "MyEvent", pp, qq
Incoming : Perform "MyEvent" → parameters received in chosen variables
```

Advantages over a 0 ms Timer:
- Safe (no parallel race condition)
- No timer instance created
- Native parameter passing

### 3.4 Keystroke

Sends a keystroke to the focused app (DAW, OS).

- Modifiers: Ctrl, Shift, Alt, Cmd (Mac), Win (Windows)
- Codes: virtual key or name (`F1`, `Esc`, `Tab`)
- Combinations and sequences supported
- **Injected** mode (Windows) or native

Incoming Keystroke: use shortcuts as triggers.

### 3.5 Variable Storage

Persists globals on disk between sessions.

| Op | Effect |
|---|---|
| `LoadAll File="N"` | load from persistent slot N |
| `SaveAll File="N"` | save |
| `Load Var="ga" File="N"` | load a single variable |
| `Save Var="ga" File="N"` | save a single variable |

On BomeBox: persistent flash. On desktop: file in the project folder.

### 3.6 Preset Action

Outgoing:
- `Activate` / `Deactivate` / `Toggle` (a preset by name or index)
- **Switcher pattern**: one "Switcher" preset deactivates all others, then activates a given one. Enables banking.

### 3.7 Project / MIDI Port

- Enable/disable the project
- Dynamically re-assign a MIDI Alias to another physical device (useful on plug/unplug)
- Incoming Port: trigger on plug/unplug

### 3.8 Mouse / Execute File / AppleScript / Serial / App Focus

Outside MIDI, but usable as outgoing actions. AppleScript is powerful on macOS (e.g. to drive a DAW through `osascript`).

---

## 4. `.bmtp` file format

Plain-text INI, signed by MT Pro. **Hand-editing a `.bmtp` is safe**: MT Pro opens the modified file and **writes a new valid signature on save**. Only MT Player requires an intact signature — so a hand-edited file must be opened and saved once in MT Pro before distribution. Files start with:
```
; ------- Bome MIDI Translator: signed project file
;
```

### 4.1 Sections

```ini
[Preset.N]
Name=...
Active=1
PresetSwitchIgnore=0
DefaultInPorts=MIDA<count><porthex><name>
DefaultOutPorts=...
Comments=
Incoming<idx>=<encoding>
Outgoing<idx>=<encoding>
Name<idx>=...
Options<idx>=<encoded options + StMa bytecode>

[Project]
DefaultInPorts=...
DefaultOutPorts=...
Version=2

[Signatures]
SigName-1=...
Signature-1=<base64>
SignedBy-1=...
```

### 4.2 Incoming/Outgoing encoding prefixes

| Prefix | Type | Example |
|---|---|---|
| `MID1` | inline raw MIDI hex | `MID1E0qqpp` = Pitch Bend ch1, LSB `qq`, MSB `pp` |
| `MID3<XML>` | typed MIDI (Simple) | `MID3<Incoming Action="MIDI"><Simple Type="ControlChange"><Channel num="0"/><Value1 num="0x03"/><Value2 var="qq" Type="SetVar"/></Simple></Incoming>` |
| `Tim0TimT<len><name>` | Timer trigger (incoming) | `Tim0TimT0007PingHUI` |
| `Tim0TimS<len><name><mode>:<ms>:<count>` | Start Timer (outgoing) | `Tim0TimS0002LP1:400:1` = "LP" Once 400 ms count 1 |
| `Prfm<XML>` | Perform trigger/action | `Prfm<Incoming Action="Perform"><Name>Init</Name><Params>pp</Params></Incoming>` |
| `EnDi02` / `EnDi03` | Project Open / Project Close events | built-in trigger |
| `KAM1...KSQ1...` | Keystroke Action / KeySequence | encodes key + modifiers |
| `VrSt<XML>` | Variable Storage | `VrSt<Outgoing Action="VarStorage" Op="LoadAll" File="1"><Name>...</Name></Outgoing>` |
| `MIDA<n>` | MIDI Alias list | `MIDA0001000DApplication-1` = 1 port, 13-char name |
| `None` | no outgoing | swallow only |

### 4.3 Options format (compiled rule bytecode)

```
Options0=Actv01Stop00OutO00StMa00000007if(pp>7)noexecutera=qq&240
         ^   |   |   |   |        ^      ^
         |   |   |   |   |        |      └ compiled rules
         |   |   |   |   |        └ NUMBER OF RULES (8 hex digits), NOT a byte size
         |   |   |   |   └ "StMa" marker = stack machine
         |   |   |   └ OutO00 (outgoing options)
         |   |   └ Stop00 (stop-after flag)
         |   └ Actv01 (translator active)
         └ prefix
```

⚠️ The field after `StMa` is a **rule count**, not a byte size. Every line below (including comments, logs and labels) counts as 1. Verified: `StMa00000011` = 0x11 = 17 rules.

The bytecode is the rules compiled into readable pseudocode. Verified tokens:
- `if(EXPR)noexecute` = condition + Exit-Skip
- `if(EXPR)execute` = condition + Exit-Execute
- `if(EXPR)skip` = condition + Skip 1
- `if(EXPR)goto<4hex><name>` = conditional Goto (e.g. `if(ga!=0)goto0002on`)
- `goto<4hex><name>` = unconditional jump (e.g. `goto0003end`)
- `label<4hex><name>` = label target (e.g. `label0002on`) — `<4hex>` = name length
- `var=expr` = assignment / expression
- `prfm><4hex>"Name", params` = Perform call (e.g. `prfm>0008"SendOn"`) — `<4hex>` = length of `"Name", params` including quotes
- `label<4hex>__cmt>// text` = comment (label name = `__cmt>` + text)
- `label<4hex>__log>Log Text %var%` = log (label name = `__log>` + text)

**Hand-editing is OK** (signatures are not blocking, see 4.1). The only real risk is a badly encoded token (mostly a wrong `StMa` count, or a malformed timer → endless ticking). Check the rule count and copy each token from an existing `.bmtp`.

---

## 5. Mackie protocols — Cheatsheet

### 5.1 MCU (Mackie Control Universal)

| Control | MIDI |
|---|---|
| Fader ch X (X = 1..8, banks of 8) | Pitch Bend channel X: `0xE0+X-1 LSB MSB` (14-bit) |
| Master fader | Pitch Bend channel 9 |
| Mute bus X | Note On ch1, note `0x10+X-1` (0x10..0x17), vel 127 = toggle |
| Solo bus X | Note ch1 `0x08+X-1` (0x08..0x0F) vel 127 |
| Select ch X | Note ch1 `0x18+X-1` (0x18..0x1F) vel 127 |
| V-Pot rotate ch X | CC ch1 `0x10+X-1` (0x10..0x17), value = signed direction (bit 6 = 0 right / 1 left, bits 0-5 = magnitude) |
| V-Pot press ch X | Note ch1 `0x20+X-1` (0x20..0x27) vel 127 |
| Button LED (feedback) | host sends Note vel 127 = on / 0 = off on the same note number |
| Snapshot / Bank switch | Program Change |
| Transport (Play/Stop/Rec/FF/Rew/Loop) | Notes ch1 `0x5B..0x5F` etc. |

**V-Pot encoding** (signed relative):
```
incoming CC value v:
  direction = (v & 0x40) ? -1 : +1
  magnitude = v & 0x3F
  delta = direction * magnitude
```

### 5.2 HUI (Pro Tools)

| Control | MIDI |
|---|---|
| Heartbeat (host→controller) | `0x90 0x00 0x00` every ~2 s — **mandatory** |
| Channel select (zone) | CC pair `0x0F` (zone select) + `0x2F` (port select) — "zone/port" protocol |
| Fader move | CC pair ch1 `0x0F+zone val_zone` + `0x2F+zone val_port` with val<<7 + val_low = 14-bit |
| Fader touch | val_port flag `0x40` |
| Fader release | val_port flag `0x00` |
| Fader move | val_port flag `0x20` |
| Button | zone+port select, then switch state via `0x2C` ON / `0x2C+0x40` OFF |
| V-Pot | CC ch1 `0x10..0x17`, same signed relative format as MCU |
| LED feedback | zone+port select + `0x2C` |

**MCU vs HUI**:
- MCU = Pitch Bend faders, Notes for buttons (stateless, simple)
- HUI = stateful CC pairs (zone/port), heartbeat required
- Bome has a **native `Simple Type="HUI"`** for the ping (`Value1="0"` = handshake)

### 5.3 Which one to choose

When the target supports both, **prefer MCU**: no ping needed, simpler encoding, less bytecode in Bome.

---

## 6. Reusable patterns

### 6.1 7-bit CC → 14-bit Pitch Bend (Mackie fader)

```
Incoming  : MID3<...><Simple Type="ControlChange"><Channel num="0"/><Value1 num="0x01"/><Value2 var="qq" Type="SetVar"/></Simple>
Rules     :
  // qq = CC value 0..127
  pp = qq * 128         // scale 7→14
  qq = pp & 0x7F        // LSB
  pp = pp >> 7          // MSB
Outgoing  : MID1 E0 qq pp     // Pitch Bend ch1
```

### 6.2 MCU mute toggle, bus N

```
Incoming  : Note ch=2 (controller pad), note number → pp
Rules     :
  pp = pp - 36 + 0x10   // remap pad note → MCU mute base
  // pp ∈ 0x10..0x17
Outgoing  : MID1 90 pp 7F     // Note On ch1 vel 127 (toggle on the target)
```

### 6.3 Relative V-Pot → parameter

```
Incoming  : CC ch=1 num=0x10 val→qq
Rules     :
  // direction bit 6, magnitude bits 0-5
  rr = qq & 0x40
  ss = qq & 0x3F
  if rr == 0 then tt = ss          // CW
  if rr != 0 then tt = 0 - ss      // CCW
  // tt = signed delta
  ga = ga + tt
  if ga < 0 then ga = 0
  if ga > 127 then ga = 127
Outgoing  : CC to the DAW with ga
```

### 6.4 HUI heartbeat

```
Preset 0 (Init), Translator 0:
  Incoming  : Project Open (EnDi02)
  Outgoing  : Tim Activate "PingHUI" Infinite 0:0:1000

Preset 0, Translator 1:
  Incoming  : Tim Trigger "PingHUI"
  Outgoing  : MID3 Simple Type="HUI" Value1="0" → Port HUI-Controller-OUT
```

### 6.5 Banking with a Switcher

```
Preset "Switcher":
  Translator "BankUp":
    Incoming  : Note (encoder press)
    Rules     : if ga >= 2 then ga = 0
                else ga = ga + 1
    Outgoing  : Perform "ApplyBank"

  Translator "ApplyBank-0":
    Incoming  : Perform "ApplyBank"
    Rules     : if ga != 0 then exit rules, skip
    Outgoing  : Preset Activate "Bank-1", Preset Deactivate "Bank-2","Bank-3"
  (same for 1, 2)
```

### 6.6 Bidirectional LED feedback

```
Host → controller:
  Incoming  : Note ch1 note=0x10 vel→pp (MCU mute LED)
  Rules     : if pp == 127 then pp = 64  // "on" color
              else pp = 0                 // off
  Outgoing  : Note ch=2 note=0x24 vel=pp → controller with velocity-based LED colors
```

---

## 7. Common pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| Uninitialized locals | random behaviour | always assign before reading |
| Global with prefix `a-f` | compile error | use `g..z` |
| 3-operand expression | error | split into 2 lines |
| HUI without heartbeat | controller goes offline ~2 s after start | add an infinite Timer |
| MCU fader jumps to zero after touch | host expects a touch Note before the fader | send Note `0x68+ch` vel 127 before the Pitch Bend (touch) |
| `Swallow` not ticked | the original message goes through **as well** | tick Swallow on the Incoming MIDI |
| Several active presets with the same incoming | translators fire in parallel | use the Switcher pattern |
| Hand-edited `.bmtp`: wrong `StMa` count | rules truncated / project won't load | `StMa` = NUMBER of rules (not bytes), recount |
| Hand-edited malformed timer (`0:0:400` instead of `1:400:1`) | timer ticks forever (read as Infinite) | format `<mode>:<ms>:<count>`, mode 1 = Once |
| OSC over Bonjour/Zeroconf | dynamic port changes | prefer MCU over OSC when possible |
| Variable Storage loses values | wrong `File="N"` slot | save explicitly before Close, or via the Project Close trigger `EnDi03` |
| Controller LED color depends on velocity | confused with mute on/off | map velocity → color explicitly (table) |

---

## 8. Recommended workflow

1. **Design in MT Pro** (GUI): create presets, capture MIDI, write rules visually.
2. **Log**: open the `Log Window` and add `Log` rules for real-time debugging.
3. **Test with the Event Monitor**: see incoming matches and outgoing variables.
4. **Keep dated `.bmtp` versions**: `Name-YYYY-MM-DD-N.bmtp`. The signature changes on every save.
5. **Version in git**: `.bmtp` is ASCII and diffable.
6. **Document**: use the preset "Comments" column + `__cmt>` in the bytecode (shown as `//` in the GUI).
7. **MT Player** only reads signed `.bmtp` files (intact signature). Use it to ship a read-only config to someone without an MT Pro license.

---

## 9. MIDI ports and aliases

```
Project → MIDI Aliases → Add Alias "Mixer-In"
                                   → can be assigned to any device at runtime
```

Benefit: a portable `.bmtp`. When moving the project to another machine, re-assign the aliases without touching the translators.

On macOS: use the **IAC Driver** for virtual ports (`Audio MIDI Setup → MIDI Studio → IAC → Device "IAC Driver" → Add bus`).

---

## 10. BomeBox specifics

- Standalone Linux hardware that runs `.bmtp` files
- No Mouse / Keystroke / AppleScript / Execute File actions
- WiFi/Ethernet MIDI (RTP-MIDI)
- Web UI at `192.168.x.x` or Bonjour `bomebox.local`
- VarStorage persisted in flash

---

## 11. Reference files

- `references/bytecode-cheatsheet.md` — full table of `.bmtp` encodings
- `references/mackie-protocol-tables.md` — full MCU/HUI tables
- `references/export-text-format.md` — the "Export Project As Text" format
- `scripts/bmtp_parser.py` / `scripts/bmtp_writer.py` — read/write the Export Text format in Python
- Official manual: https://download.bome.com/manuals/miditranslator_manual.pdf (section 10 = Rules)
- Forum: https://forum.bome.com
