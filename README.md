# Bome MIDI Translator Pro — Claude Skill

A [Claude Code](https://claude.com/claude-code) skill that gives Claude a solid working knowledge of **Bome MIDI Translator Pro**: rules syntax, variables, actions, the `.bmtp` file format, and the Mackie MCU / HUI protocols.

> I have been using this skill for about a year in my own MIDI setups. In my use, it no longer makes any mistakes.

## What it covers

- **Rules language**: local vs global variables, operators, the 2-operand limit, conditionals, goto/labels, Perform, Log
- **Actions**: MIDI (raw and typed), Timer, Perform, Keystroke, Preset, Variable Storage, Project/Ports
- **`.bmtp` file format**: sections, encoding prefixes (`MID1`, `MID3`, `Tim0`, `Prfm`, `EnDi`, `VrSt`, `MIDA`), the `StMa` rule bytecode — enough to read and hand-edit project files safely
- **Mackie protocols**: full MCU and HUI tables (faders, V-Pots, buttons, LEDs, LCD, meters, HUI heartbeat)
- **Ready-made patterns**: 7-bit CC → 14-bit Pitch Bend, relative V-Pot decoding, banking with a Switcher preset, LED feedback, HUI heartbeat
- **Common pitfalls** and how to avoid them
- **Python helpers** to parse and write the "Export Project As Text" format

## Install

Copy the skill folder into your Claude skills directory:

```bash
git clone https://github.com/Ego1-Techno/bome-midi-translator-skill.git
cp -R bome-midi-translator-skill/skills/bome-midi-translator ~/.claude/skills/
```

Claude loads it automatically whenever you talk about Bome, MT Pro, BomeBox, `.bmtp` files, translators, or Mackie MCU/HUI.

## Layout

```
skills/bome-midi-translator/
├── SKILL.md                         main reference
├── references/
│   ├── bytecode-cheatsheet.md       .bmtp encodings
│   ├── mackie-protocol-tables.md    full MCU / HUI tables
│   └── export-text-format.md        "Export Project As Text" format
├── examples/                        small example projects (export text)
└── scripts/
    ├── bmtp_parser.py               parse export text → Python / JSON
    └── bmtp_writer.py               build export text from Python
```

Quick test of the scripts (Python 3.10+):

```bash
cd skills/bome-midi-translator/scripts
python3 bmtp_parser.py ../examples/cc-to-mcu-fader.txt
```

## Disclaimer

Not affiliated with Bome Software. "Bome MIDI Translator" is a trademark of its owner. Always keep a backup of your `.bmtp` files before hand-editing them.

## License

MIT
