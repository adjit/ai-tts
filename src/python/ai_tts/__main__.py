"""CLI entry: python -m ai_tts <command>

Scaffold only. Real commands land in platforms.md Phase 1.
"""

from __future__ import annotations

import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help", "help"}:
        print(
            "ai-tts (scaffold)\n"
            "\n"
            "Planned commands:\n"
            "  speak TEXT       One-shot TTS (direct mode)\n"
            "  daemon           Run optional low-latency server\n"
            "  toggle           Toggle per-directory /tts marker\n"
            "  hook-state       SessionStart helper\n"
            "  hook-stop        Stop helper (read JSON on stdin)\n"
            "\n"
            "See docs/platforms.md for the multi-OS plan.\n"
            "Windows production path today: install.ps1 + PowerShell runtime.\n"
        )
        return 0

    cmd = argv[0]
    print(
        f"ai-tts: command {cmd!r} is not implemented yet "
        f"(Python portable core is scaffold-only).\n"
        f"Use the Windows PowerShell installer for now, or track docs/platforms.md.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
