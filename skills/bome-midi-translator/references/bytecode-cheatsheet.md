# `.bmtp` Bytecode Cheatsheet

Decoding table for the encodings found in signed `.bmtp` files.

## Incoming/Outgoing prefixes

| Prefix | Type | Format | Example |
|---|---|---|---|
| `MID1` | inline raw MIDI bytes | `MID1<hex+vars>` | `MID1E0qqpp` |
| `MID3` | typed MIDI (inline XML) | `MID3<XML>` | see below |
| `Tim0TimT<len:4hex><name>` | Incoming Timer Trigger | name length, then name | `Tim0TimT0007PingHUI` (len=7) |
| `Tim0TimS<len:4hex><name><mode>:<ms>:<count>` | Outgoing Timer Start | name + timing | `Tim0TimS0002LP1:400:1` |
| `Tim0TimK<len:4hex><name>` | Outgoing Timer Kill | — | `Tim0TimK0007PingHUI` |
| `Prfm<XML>` | Perform (in/out) | inline XML | `Prfm<Incoming Action="Perform"><Name>Init</Name><Params>pp</Params></Incoming>` |
| `EnDi02` | Built-in: Project Open | — | used to init globals |
| `EnDi03` | Built-in: Project Close | — | used to save VarStorage |
| `EnDi04` | Built-in: Project init complete | — | — |
| `KAM1<key>` | Keystroke in/out — Key As Modifier | — | `KAM10000` (no modifier) |
| `KSQ1<count><key+state>` | KeySequence | sequence of keys | `KSQ1000201B21B` |
| `VrSt<XML>` | Variable Storage | XML | `VrSt<Outgoing Action="VarStorage" Op="LoadAll" File="1"><Name>SlotName</Name></Outgoing>` |
| `MIDA<count:4hex><portlen:4hex><portname>...` | Port list (MIDI Aliases) | repeated | `MIDA0001000FHUI-Controller1` |
| `None` | no outgoing (swallow only) | — | `Outgoing0=None` |

## Timer timing format

```
Tim0TimS<len><name><mode>:<ms>:<count>
```

- `mode` 1 = Once. A malformed value (e.g. `0:0:400`) can be read as Infinite → the timer ticks forever.
- Example: `Tim0TimS0002LP1:400:1` = timer "LP", Once, 400 ms, count 1.
- Always copy the exact format from an existing `.bmtp` saved by MT Pro.

## Translator Options field

```
Options<idx>=Actv<n>Stop<n>OutO<n>StMa<count:8hex><bytecode>
```

| Field | Values | Meaning |
|---|---|---|
| `Actv00` / `Actv01` | 0/1 | translator active |
| `Stop00` / `Stop01` | 0/1 | stop processing after this translator |
| `OutO00` / `OutO01` | 0/1 | outgoing options flag (delay, routing, etc.) |
| `StMa<count>` | 8 hex digits | **number of rules** (not a byte length). Comments, logs and labels count as 1 each |

## StMa bytecode — readable pseudocode

The bytecode is close to literal pseudocode:

| Token | Meaning |
|---|---|
| `pp=qq` | assignment |
| `pp=qq+rr` | expression |
| `if(EXPR)skip` | conditional → Skip 1 |
| `if(EXPR)skip2` | conditional → Skip 2 |
| `if(EXPR)execute` | conditional → Exit Execute |
| `if(EXPR)noexecute` | conditional → Exit Ignore |
| `if(EXPR)goto<len:4hex><label>` | conditional → Goto |
| `goto<len:4hex><label>` | direct goto |
| `noexecute` | Exit Ignore (unconditional) |
| `execute` | Exit Execute (unconditional) |
| `label<len:4hex><name>` | label declaration |
| `label<len:4hex>__cmt>// text` | line comment (visible in the GUI) |
| `label<len:4hex>__log>Log "text %var%"` | log rule |
| `prfm><len:4hex>"name", p1, p2` | Perform call |

`label` format:
```
label0006__cmt>
     ^^^^
     4 hex = payload length (in chars), including the __cmt> prefix or the name
```

## Simple Type XML encoding

```xml
<Simple Type="<TypeName>">
  <Channel num="<0-15 or var>"/>
  <Value1 num="<hex/dec>" [var="xx" Type="SetVar"]/>
  <Value2 num="<hex/dec>" [var="xx" Type="SetVar"]/>
</Simple>
```

Valid types:
- `NoteOn`, `NoteOff`, `PolyPressure`
- `ControlChange`
- `ProgramChange` (no Value2)
- `ChannelPressure` (no Value2)
- `PitchBend`
- `HUI` (handshake)
- `MPE`

`Channel num="0"` = MIDI ch1 (zero-indexed internally).

## MIDI Alias encoding (MIDA)

```
MIDA<port_count:4hex>(<name_len:4hex><name_ascii>)*
```

Example: `MIDA0003000DApplication-1000DApplication-2000FHUI-Controller2`
- `0003` = 3 ports
- `000D Application-1` = port 1 (13 chars)
- `000D Application-2` = port 2
- `000F HUI-Controller2` = port 3 (15 chars)

## Signature

```ini
[Signatures]
SigName-1=[Midi Translator Pro Internal]
Signature-1=<base64>
SignedBy-1=<license holder>
```

Any manual edit **invalidates** the signature → MT Player refuses the file, MT Pro accepts it (and re-signs on save).
