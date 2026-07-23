---
name: tts
description: Toggle xAI voice output (spoken text-to-speech of my responses) on or off for the CURRENT directory. Voice is off by default per directory. Use when the user runs /tts.
disable-model-invocation: true
user-invocable: true
---

Toggle voice output for the **current working directory** and report the new state. Run this exact command with the shell tool (it keys off the directory, so the choice persists for this project across sessions and does not affect other directories):

```
$slash = [char]92; $fwd = [char]47
$d = (Get-Location).Path.TrimEnd($slash,$fwd).ToLowerInvariant()
$md5 = [System.Security.Cryptography.MD5]::Create()
$key = ([System.BitConverter]::ToString($md5.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($d)))).Replace('-','').ToLower()
$dir = Join-Path $env:USERPROFILE '.grok\.tts-dirs'
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
$f = Join-Path $dir $key
$voice = 'carina'
$cfg = Join-Path $env:USERPROFILE '.ai-tts\config.json'
if (Test-Path $cfg) { try { $voice = (Get-Content $cfg -Raw | ConvertFrom-Json).voice } catch {} }
if ([System.IO.File]::Exists($f)) { [System.IO.File]::Delete($f); "TTS OFF for this directory: $d" }
else { [System.IO.File]::WriteAllText($f,'on'); "TTS ON for this directory: $d (voice: $voice)" }
```

Then tell the user the new state in one short line:

- If it printed **TTS ON**: from now on (in this directory), end each response with a concise `<say>...</say>` spoken summary (1–2 sentences, plain spoken language — no code, paths, or markdown). A Stop hook speaks it asynchronously via xAI.
- If it printed **TTS OFF**: stop emitting `<say>` markers.

Voice is OFF by default in every directory. State is stored under `~/.grok/.tts-dirs/` (separate from Claude Code).
