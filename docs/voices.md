# xAI TTS voices

## Prefer the CLI

```bash
ai-tts voices                          # known voice ids (offline list)
ai-tts config set voice eve            # default voice in config.json
ai-tts config set speed 1.1            # typically 0.7–1.5
ai-tts speak --voice leo "Hello"       # one-shot override
ai-tts status                          # shows current default voice
```

Windows (after install / PATH):

```powershell
ai-tts voices
ai-tts config set voice carina
ai-tts speak --voice carina "Hello"
```

## Config file (equivalent)

Defaults live in `~/.ai-tts/config.json` (or `$AI_TTS_HOME/config.json`):

```json
{
  "voice": "carina",
  "language": "en",
  "speed": 1.0
}
```

Prefer `ai-tts config set …` over hand-editing when possible.

> **Deprecated:** PowerShell `speak.ps1 -Voice …` is a Windows fallback only.
> Use `ai-tts speak --voice …`. See [DEPRECATED_POWERSHELL.md](DEPRECATED_POWERSHELL.md).

## Common voices

| voice_id | Name | Gender (API) |
|----------|------|--------------|
| `carina` | Carina | female |
| `ara` | Ara | female |
| `eve` | Eve | female |
| `luna` | Luna | female |
| `iris` | Iris | female |
| `celeste` | Celeste | female |
| `leo` | Leo | male |
| `rex` | Rex | male |
| `sal` | Sal | male |
| `orion` | Orion | male |
| `atlas` | Atlas | male |

`ai-tts voices` prints this catalog offline. The live xAI catalog may grow over time.

### Live catalog (optional, needs `XAI_API_KEY`)

```bash
# Example with curl
curl -sS -H "Authorization: Bearer $XAI_API_KEY" \
  https://api.x.ai/v1/tts/voices | jq .
```

```powershell
$k = $env:XAI_API_KEY
if (-not $k) { $k = [Environment]::GetEnvironmentVariable('XAI_API_KEY','User') }
(Invoke-RestMethod -Uri 'https://api.x.ai/v1/tts/voices' -Headers @{ Authorization = "Bearer $k" }).voices |
  Select-Object voice_id, name, gender | Format-Table
```

Speed range is typically **0.7–1.5**.
