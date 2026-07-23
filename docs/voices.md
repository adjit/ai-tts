# xAI TTS voices

Set the default in `~/.ai-tts/config.json`:

```json
{
  "voice": "carina",
  "language": "en",
  "speed": 1.0
}
```

Or one-shot:

```powershell
powershell -File $env:USERPROFILE\.ai-tts\speak.ps1 -Text "Hello" -Voice carina
```

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

List all voices (requires `XAI_API_KEY`):

```powershell
$k = $env:XAI_API_KEY
if (-not $k) { $k = [Environment]::GetEnvironmentVariable('XAI_API_KEY','User') }
(Invoke-RestMethod -Uri 'https://api.x.ai/v1/tts/voices' -Headers @{ Authorization = "Bearer $k" }).voices |
  Select-Object voice_id, name, gender | Format-Table
```

Speed range is typically **0.7–1.5**.
