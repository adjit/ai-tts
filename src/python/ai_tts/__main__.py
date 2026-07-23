"""CLI: python -m ai_tts <command> ..."""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(
        prog="ai-tts",
        description="Portable xAI TTS for Grok Build and Claude Code",
    )
    sub = parser.add_subparsers(dest="cmd", required=False)

    p_speak = sub.add_parser("speak", help="Synthesize and play text (direct path)")
    p_speak.add_argument("text", nargs="*", help="Text to speak")
    p_speak.add_argument("--voice", default=None)
    p_speak.add_argument("--language", default=None)
    p_speak.add_argument("--speed", type=float, default=None)
    p_speak.add_argument(
        "--transport",
        choices=["auto", "stream", "rest"],
        default="auto",
    )
    p_speak.add_argument("--json", action="store_true", help="Print timing JSON")

    p_daemon = sub.add_parser("daemon", help="Run optional TCP daemon")
    p_daemon.add_argument("--host", default=None)
    p_daemon.add_argument("--port", type=int, default=None)
    p_daemon.add_argument(
        "--enable-config",
        action="store_true",
        help="Set mode=daemon in config.json",
    )

    p_stopd = sub.add_parser("daemon-stop", help="Ask daemon to shut down")
    p_ping = sub.add_parser("daemon-ping", help="Ping daemon")

    p_toggle = sub.add_parser("toggle", help="Toggle /tts marker for a directory")
    p_toggle.add_argument("--cwd", default=None)
    p_toggle.add_argument(
        "--harness",
        choices=["grok", "claude"],
        default="grok",
    )

    p_state = sub.add_parser("hook-state", help="SessionStart hook")
    p_state.add_argument("--harness", choices=["grok", "claude"], default="grok")

    p_hstop = sub.add_parser("hook-stop", help="Stop hook")
    p_hstop.add_argument("--harness", choices=["grok", "claude"], default="grok")

    p_probe = sub.add_parser("probe", help="Show players / config / stream availability")

    # Allow: python -m ai_tts speak -- hello world
    # and bare help
    if not argv or argv[0] in {"-h", "--help", "help"}:
        parser.print_help()
        print(
            "\nExamples:\n"
            '  python -m ai_tts speak "Hello from Carina"\n'
            "  python -m ai_tts daemon\n"
            "  python -m ai_tts toggle --harness grok\n"
            "  python -m ai_tts probe\n"
        )
        return 0

    args = parser.parse_args(argv)

    if args.cmd == "speak":
        from .client import DaemonClientError, speak_via_daemon
        from .config import load_config
        from .speak import speak_text
        from .tts_rest import TtsError

        text = " ".join(args.text).strip()
        if not text:
            print("ai-tts speak: missing text", file=sys.stderr)
            return 2
        cfg = load_config()
        try:
            meta = None
            # Prefer warm TCP daemon when enabled (unless transport forced to rest/stream local)
            if cfg.daemon_enabled and args.transport == "auto":
                try:
                    meta = speak_via_daemon(
                        text,
                        voice=args.voice,
                        language=args.language,
                        speed=args.speed,
                        cfg=cfg,
                    )
                    meta = dict(meta)
                    meta.setdefault("transport", "daemon")
                except DaemonClientError:
                    meta = None
            if meta is None:
                meta = speak_text(
                    text,
                    voice=args.voice,
                    language=args.language,
                    speed=args.speed,
                    transport=args.transport,
                    cfg=cfg,
                )
        except TtsError as e:
            print(f"ai-tts speak failed: {e}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(meta))
        else:
            print(
                f"ok transport={meta.get('transport')} voice={meta.get('voice')} "
                f"ms={meta.get('ms')}"
            )
        return 0

    if args.cmd == "daemon":
        from .config import load_config, save_config
        from .daemon_server import mark_config_daemon_enabled, serve

        cfg = load_config()
        if args.host:
            cfg.daemon.host = args.host
        if args.port:
            cfg.daemon.port = args.port
        if args.enable_config:
            mark_config_daemon_enabled(True)
            cfg = load_config()
        if args.host or args.port:
            save_config(cfg)
        serve(cfg)
        return 0

    if args.cmd == "daemon-stop":
        from .client import DaemonClientError, shutdown_daemon
        from .config import load_config, save_config

        try:
            print(json.dumps(shutdown_daemon()))
        except DaemonClientError as e:
            print(f"daemon-stop: {e}", file=sys.stderr)
            return 1
        cfg = load_config()
        cfg.mode = "direct"
        cfg.daemon.enabled = False
        save_config(cfg)
        return 0

    if args.cmd == "daemon-ping":
        from .client import DaemonClientError, ping_daemon

        try:
            print(json.dumps(ping_daemon()))
            return 0
        except DaemonClientError as e:
            print(f"daemon-ping: {e}", file=sys.stderr)
            return 1

    if args.cmd == "toggle":
        from .config import load_config
        from .markers import toggle

        on, cwd = toggle(args.cwd, args.harness)
        voice = load_config().voice
        if on:
            print(f"TTS ON for this directory: {cwd} (voice: {voice}) harness={args.harness}")
        else:
            print(f"TTS OFF for this directory: {cwd} harness={args.harness}")
        return 0

    if args.cmd == "hook-state":
        from .hooks import hook_state

        return hook_state(args.harness)

    if args.cmd == "hook-stop":
        from .hooks import hook_stop

        return hook_stop(args.harness)

    if args.cmd == "probe":
        from .config import get_api_key, load_config
        from .play import probe_players
        from .tts_stream import streaming_available

        cfg = load_config()
        print("config:", json.dumps({
            "voice": cfg.voice,
            "mode": cfg.mode,
            "daemon_enabled": cfg.daemon_enabled,
            "host": cfg.daemon.host,
            "port": cfg.daemon.port,
        }))
        print("players:", ", ".join(probe_players()) or "(none)")
        print("streaming_websockets:", streaming_available())
        print("XAI_API_KEY:", "set" if get_api_key() else "MISSING")
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
