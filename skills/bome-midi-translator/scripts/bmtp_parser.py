#!/usr/bin/env python3
"""Parser for Bome MIDI Translator Pro files (Export Text format).

Usage:
    project = parse_file("my_project.txt")
    # or from a string:
    project = parse_text(text)

Returned structure:
    {
        "presets": [
            {
                "index": 0,
                "name": "Init",
                "active": True,
                "translators": [
                    {
                        "index": "0.0",
                        "name": "...",
                        "active": True,
                        "options": ["swallow"],
                        "incoming": "MIDI B0 07 pp",
                        "rules": ["ga = 0", "// comment"],
                        "outgoing": "MIDI E0 rr pp"
                    }
                ]
            }
        ],
        "variables": {"ga": 2, "gb": 24}
    }
"""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Translator:
    index: str
    name: str
    active: bool
    options: list[str]
    incoming: str
    rules: list[str]
    outgoing: str


@dataclass
class Preset:
    index: int
    name: str
    active: bool
    translators: list[Translator] = field(default_factory=list)


@dataclass
class Project:
    presets: list[Preset] = field(default_factory=list)
    variables: dict[str, int] = field(default_factory=dict)


_RE_PRESET = re.compile(r'^\[(x| )\] Preset (\d+): (.+)$')
_RE_TRANSLATOR = re.compile(r'^\[(x| )\] Translator ([\d.]+): (.+)$')
_RE_VAR = re.compile(r'^([a-z][a-z0-9])=(-?\d+)$')


def parse_text(text: str) -> Project:
    project = Project()
    current_preset: Preset | None = None
    current_translator: Translator | None = None
    section: str | None = None  # "rules" | None

    def flush_translator():
        nonlocal current_translator
        if current_translator and current_preset:
            current_preset.translators.append(current_translator)
            current_translator = None

    for raw in text.splitlines():
        line = raw.strip()

        # skip comments and empty
        if not line or line.startswith(';'):
            continue

        # Variable storage line (ga=2)
        m = _RE_VAR.match(line)
        if m and current_preset is None and current_translator is None:
            project.variables[m.group(1)] = int(m.group(2))
            continue

        # Preset header
        m = _RE_PRESET.match(line)
        if m:
            flush_translator()
            current_preset = Preset(
                index=int(m.group(2)),
                name=m.group(3).strip(),
                active=m.group(1) == 'x',
            )
            project.presets.append(current_preset)
            current_translator = None
            section = None
            continue

        # Translator header
        m = _RE_TRANSLATOR.match(line)
        if m:
            flush_translator()
            current_translator = Translator(
                index=m.group(2),
                name=m.group(3).strip(),
                active=m.group(1) == 'x',
                options=[],
                incoming='',
                rules=[],
                outgoing='',
            )
            section = None
            continue

        if current_translator is None:
            continue

        # Section headers
        if line.startswith('Options:'):
            section = None
            opts = line[len('Options:'):].strip()
            current_translator.options = [o.strip() for o in opts.split(',') if o.strip()]
            continue

        if line.startswith('Incoming:'):
            section = None
            current_translator.incoming = line[len('Incoming:'):].strip()
            continue

        if line.startswith('Rules:'):
            section = 'rules'
            rest = line[len('Rules:'):].strip()
            if rest:
                current_translator.rules.append(rest)
            continue

        if line.startswith('Outgoing:'):
            section = None
            current_translator.outgoing = line[len('Outgoing:'):].strip()
            continue

        # Body of Rules
        if section == 'rules':
            current_translator.rules.append(line)

    flush_translator()
    return project


def parse_file(path: str) -> Project:
    with open(path, encoding='utf-8') as f:
        return parse_text(f.read())


def to_dict(project: Project) -> dict[str, Any]:
    return {
        "presets": [
            {
                "index": p.index,
                "name": p.name,
                "active": p.active,
                "translators": [
                    {
                        "index": t.index,
                        "name": t.name,
                        "active": t.active,
                        "options": t.options,
                        "incoming": t.incoming,
                        "rules": t.rules,
                        "outgoing": t.outgoing,
                    }
                    for t in p.translators
                ],
            }
            for p in project.presets
        ],
        "variables": project.variables,
    }


if __name__ == "__main__":
    import sys, json

    if len(sys.argv) < 2:
        print("Usage: bmtp_parser.py <file.txt>")
        sys.exit(1)

    proj = parse_file(sys.argv[1])
    print(json.dumps(to_dict(proj), indent=2, ensure_ascii=False))
