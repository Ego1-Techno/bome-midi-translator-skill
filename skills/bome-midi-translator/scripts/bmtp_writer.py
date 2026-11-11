#!/usr/bin/env python3
"""Builder for the Export Text format of Bome MIDI Translator Pro.

Usage:
    from bmtp_parser import Project, Preset, Translator
    from bmtp_writer import to_text, write_file

    p = Project()
    preset = Preset(index=0, name="Init", active=True)
    t = Translator(
        index="0.0",
        name="CC7 to PitchBend",
        active=True,
        options=["swallow"],
        incoming="MIDI B0 07 pp",
        rules=["qq = pp * 128", "rr = qq & 0x7F", "pp = qq >> 7"],
        outgoing="MIDI E0 rr pp",
    )
    preset.translators.append(t)
    p.presets.append(preset)
    print(to_text(p))
"""

from bmtp_parser import Project, Preset, Translator


def _state(active: bool) -> str:
    return 'x' if active else ' '


def translator_to_text(t: Translator) -> str:
    lines = [f"[{_state(t.active)}] Translator {t.index}: {t.name}"]

    opts = ', '.join(t.options) if t.options else ''
    lines.append(f"Options: {opts}")

    lines.append(f"Incoming: {t.incoming}")

    if t.rules:
        lines.append("Rules:")
        for r in t.rules:
            lines.append(f"  {r}")
    else:
        lines.append("Rules:")

    lines.append(f"Outgoing: {t.outgoing}")
    return '\n'.join(lines)


def preset_to_text(p: Preset) -> str:
    lines = [f"[{_state(p.active)}] Preset {p.index}: {p.name}"]
    lines.append('')
    for t in p.translators:
        lines.append(translator_to_text(t))
        lines.append('')
    return '\n'.join(lines)


def to_text(project: Project) -> str:
    parts = []

    for preset in project.presets:
        parts.append(preset_to_text(preset))

    if project.variables:
        parts.append('\n'.join(f"{k}={v}" for k, v in sorted(project.variables.items())))

    return '\n'.join(parts).strip() + '\n'


def write_file(project: Project, path: str) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(to_text(project))


# --- Quick helpers ---

def make_translator(
    index: str,
    name: str,
    incoming: str,
    rules: list[str],
    outgoing: str,
    options: list[str] | None = None,
    active: bool = True,
) -> Translator:
    return Translator(
        index=index,
        name=name,
        active=active,
        options=options or [],
        incoming=incoming,
        rules=rules,
        outgoing=outgoing,
    )


def make_preset(index: int, name: str, translators: list[Translator], active: bool = True) -> Preset:
    p = Preset(index=index, name=name, active=active)
    p.translators = translators
    return p


if __name__ == "__main__":
    from bmtp_parser import Project

    proj = Project()

    t = make_translator(
        index="0.0",
        name="CC7 → PitchBend MCU",
        incoming="MIDI B0 07 pp",
        rules=[
            "// scale 7-bit → 14-bit",
            "qq = pp * 128",
            "rr = qq & 0x7F",
            "pp = qq >> 7",
        ],
        outgoing="MIDI E0 rr pp",
        options=["swallow"],
    )
    proj.presets.append(make_preset(0, "MCU Fader", [t]))
    print(to_text(proj))
