# Voice Output (TTS)

Voice output is delivered by a **Stop hook** that speaks a `<say>` line asynchronously via xAI — you do **NOT** call `speak.ps1` yourself (that would block the turn and waste context).

**How it works:**

- Voice is **per-directory and OFF by default.** A SessionStart hook reports the state: `[tts] Voice output is ON for this directory` or `OFF`. The `/tts` skill toggles the current directory (the choice persists under `~/.claude/.tts-dirs/`).
- **When ON:** end every response with a single `<say>...</say>` line containing a concise, conversational spoken summary of the response.
- **When OFF:** do not emit `<say>` markers at all.

**Writing the `<say>` line:**

- 1–2 sentences, like a colleague giving a quick verbal summary of what you just did or found.
- Plain spoken language only — no code, file paths, markdown, or long identifiers.
- Place it as the final line of your response.

> Tip: paste this file into `~/.claude/CLAUDE.md` or `~/.claude/rules/`, or let `install.ps1 -Target Claude` copy it for you.
