"""Pretty install presentation (Rich when available, plain fallback).

Used by install.sh:

  python -m ai_tts.install_ui banner ...
  python -m ai_tts.install_ui step "..."
  python -m ai_tts.install_ui wizard --export-shell
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .voices import KNOWN_VOICES, VOICE_META

_RICH = False
try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Confirm, Prompt
    from rich.table import Table
    from rich.text import Text
    from rich.theme import Theme

    _RICH = True
except ImportError:  # pragma: no cover - exercised via plain fallback tests
    Console = None  # type: ignore[misc, assignment]


def _console() -> Any:
    if not _RICH:
        return None
    theme = Theme(
        {
            "info": "cyan",
            "ok": "bold green",
            "warn": "bold yellow",
            "err": "bold red",
            "muted": "dim",
            "title": "bold magenta",
        }
    )
    return Console(theme=theme, highlight=False)


def cmd_banner(args: argparse.Namespace) -> int:
    title = args.title or "ai-tts installer"
    rows = []
    if args.target:
        rows.append(("target", args.target))
    if args.voice:
        rows.append(("voice", args.voice))
    if args.python:
        rows.append(("python", args.python))
    if args.home:
        rows.append(("home", args.home))
    if args.mode:
        rows.append(("mode", args.mode))

    c = _console()
    if c is None:
        print(f"==> {title}")
        for k, v in rows:
            print(f"  {k:8} : {v}")
        print()
        return 0

    table = Table(show_header=False, box=box.SIMPLE, pad_edge=False)
    table.add_column(style="muted")
    table.add_column(style="bold")
    for k, v in rows:
        table.add_row(k, v)
    c.print(
        Panel(
            table,
            title=f"[title]{title}[/title]",
            subtitle="[muted]xAI spoken agent summaries[/muted]",
            border_style="magenta",
            padding=(1, 2),
        )
    )
    c.print()
    return 0


def cmd_step(args: argparse.Namespace) -> int:
    msg = " ".join(args.message)
    c = _console()
    if c is None:
        print(f"-> {msg}")
        return 0
    c.print(f"[info]→[/info] {msg}")
    return 0


def cmd_ok(args: argparse.Namespace) -> int:
    msg = " ".join(args.message)
    c = _console()
    if c is None:
        print(f"  OK {msg}")
        return 0
    c.print(f"  [ok]✓[/ok] {msg}")
    return 0


def cmd_warn(args: argparse.Namespace) -> int:
    msg = " ".join(args.message)
    c = _console()
    if c is None:
        print(f"  ! {msg}")
        return 0
    c.print(f"  [warn]![/warn] {msg}")
    return 0


def cmd_error(args: argparse.Namespace) -> int:
    msg = " ".join(args.message)
    c = _console()
    if c is None:
        print(f"error: {msg}", file=sys.stderr)
        return 1
    c.print(f"[err]error:[/err] {msg}", style="err")
    return 1


def cmd_next_steps(args: argparse.Namespace) -> int:
    """Pretty post-install checklist."""
    launcher = args.launcher or "ai-tts"
    env_sh = args.env_sh or "~/.ai-tts/env.sh"
    lines = [
        ("1. API key", "export XAI_API_KEY=...  # https://console.x.ai"),
        ("2. PATH", f"source {env_sh}   # or ensure ~/.local/bin is on PATH"),
        ("3. Health", f"{launcher} doctor"),
        ("4. Speak", f'{launcher} speak "Hello from Carina"'),
        ("5. Agent", "New Grok session → /tts in a project"),
        ("Uninstall", f"{launcher} uninstall   # or ./uninstall.sh"),
    ]
    c = _console()
    if c is None:
        print()
        print("Next steps:")
        for title, body in lines:
            print(f"  {title}: {body}")
        print("Done.")
        return 0

    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Step")
    table.add_column("Action")
    for title, body in lines:
        table.add_row(title, body)
    c.print()
    c.print(
        Panel(
            table,
            title="[ok]Install complete[/ok]",
            border_style="green",
            padding=(1, 1),
        )
    )
    c.print("[muted]Tip: run [bold]ai-tts doctor[/bold] anytime to re-check your setup.[/muted]")
    return 0


def _pick_from_list(
    label: str,
    options: list[str],
    *,
    default: str,
    descriptions: dict[str, str] | None = None,
) -> str:
    descriptions = descriptions or {}
    c = _console()
    default = default if default in options else options[0]

    if c is None or not sys.stdin.isatty():
        # Non-interactive / plain: keep default
        return default

    c.print()
    c.print(Text(label, style="bold"))
    for i, opt in enumerate(options, 1):
        mark = " [dim](default)[/dim]" if opt == default else ""
        desc = descriptions.get(opt, "")
        extra = f" — {desc}" if desc else ""
        c.print(f"  [cyan]{i}[/cyan]. [bold]{opt}[/bold]{mark}{extra}")

    while True:
        raw = Prompt.ask(
            "Choice",
            default=str(options.index(default) + 1),
        ).strip()
        if not raw:
            return default
        if raw in options:
            return raw
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        c.print("[warn]Pick a number or exact name from the list.[/warn]")


def cmd_wizard(args: argparse.Namespace) -> int:
    """Interactive choices → print shell exports or JSON."""
    targets = ["Grok", "Claude", "Both"]
    target_desc = {
        "Grok": "Grok Build hooks + /tts skill",
        "Claude": "Claude Code skill + hook snippet",
        "Both": "Grok and Claude",
    }
    voices = list(KNOWN_VOICES)
    voice_desc = {
        v: f"{VOICE_META.get(v, {}).get('name', v)} "
        f"({VOICE_META.get(v, {}).get('gender', '')})".strip()
        for v in voices
    }

    c = _console()
    if c is not None:
        c.print(
            Panel.fit(
                "[title]ai-tts interactive install[/title]\n"
                "[muted]Pick a harness and default voice. "
                "Press Enter to accept defaults.[/muted]",
                border_style="magenta",
            )
        )
    else:
        print("ai-tts interactive install (plain mode)")

    default_target = args.default_target or "Grok"
    default_voice = args.default_voice or "carina"
    target = _pick_from_list(
        "Install target",
        targets,
        default=default_target,
        descriptions=target_desc,
    )
    voice = _pick_from_list(
        "Default voice",
        voices,
        default=default_voice if default_voice in voices else "carina",
        descriptions=voice_desc,
    )

    enable_daemon = False
    if c is not None and sys.stdin.isatty():
        enable_daemon = Confirm.ask(
            "Enable low-latency daemon mode in config?",
            default=False,
        )
    force = False
    if c is not None and sys.stdin.isatty():
        force = Confirm.ask(
            "Overwrite existing config.json if present?",
            default=False,
        )

    result = {
        "TARGET": target,
        "VOICE": voice,
        "ENABLE_DAEMON": "1" if enable_daemon else "0",
        "FORCE": "1" if force else "0",
    }

    if args.export_shell:
        for k, v in result.items():
            # Safe for eval in bash (values are controlled)
            print(f"{k}={shlex_quote(v)}")
        return 0

    if args.json:
        print(json.dumps(result))
        return 0

    # Human summary
    if c is None:
        print(result)
    else:
        t = Table(box=box.SIMPLE, show_header=False)
        t.add_column(style="muted")
        t.add_column(style="bold")
        for k, v in result.items():
            t.add_row(k, v)
        c.print(Panel(t, title="[ok]Selections[/ok]", border_style="green"))
    return 0


def shlex_quote(s: str) -> str:
    """Minimal shell quoting without importing shlex for clarity in tests."""
    if not s:
        return "''"
    if all(c.isalnum() or c in "._-/" for c in s):
        return s
    return "'" + s.replace("'", "'\"'\"'") + "'"


def cmd_have_rich(_: argparse.Namespace) -> int:
    print("1" if _RICH else "0")
    return 0


def cmd_ensure_rich(_: argparse.Namespace) -> int:
    """Best-effort: report whether Rich is importable (install.sh may pip install)."""
    if _RICH:
        print("rich: ready")
        return 0
    print("rich: missing", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="ai-tts.install_ui", description="Install UI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("banner", help="Install header panel")
    p.add_argument("--title", default="ai-tts installer")
    p.add_argument("--target", default="")
    p.add_argument("--voice", default="")
    p.add_argument("--python", default="")
    p.add_argument("--home", default="")
    p.add_argument("--mode", default="")

    for name in ("step", "ok", "warn", "error"):
        sp = sub.add_parser(name)
        sp.add_argument("message", nargs="+")

    pns = sub.add_parser("next-steps", help="Post-install checklist")
    pns.add_argument("--launcher", default="")
    pns.add_argument("--env-sh", default="")

    pw = sub.add_parser("wizard", help="Interactive target/voice picker")
    pw.add_argument("--export-shell", action="store_true")
    pw.add_argument("--json", action="store_true")
    pw.add_argument("--default-target", default="Grok")
    pw.add_argument("--default-voice", default="carina")

    sub.add_parser("have-rich")
    sub.add_parser("ensure-rich")

    args = parser.parse_args(argv)
    dispatch = {
        "banner": cmd_banner,
        "step": cmd_step,
        "ok": cmd_ok,
        "warn": cmd_warn,
        "error": cmd_error,
        "next-steps": cmd_next_steps,
        "wizard": cmd_wizard,
        "have-rich": cmd_have_rich,
        "ensure-rich": cmd_ensure_rich,
    }
    return dispatch[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
