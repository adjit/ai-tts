# Shared speak implementation (REST + optional streaming WebSocket).
# Dot-sourced by speak.ps1 and daemon.ps1 — not meant to be run alone.

function Get-AiTtsApiKey {
    $key = $env:XAI_API_KEY
    if (-not $key) { $key = [System.Environment]::GetEnvironmentVariable('XAI_API_KEY', 'User') }
    return $key
}

function Ensure-WinMM {
    if (-not ('Native.WinMM' -as [type])) {
        Add-Type -Name WinMM -Namespace Native -MemberDefinition @'
[DllImport("winmm.dll", CharSet = CharSet.Auto)]
public static extern int mciSendString(string command, System.Text.StringBuilder buffer, int bufferSize, System.IntPtr hwndCallback);
'@
    }
}

function Play-WavFile([string]$path) {
    Ensure-WinMM
    $alias = "aitts$PID$(Get-Random -Maximum 99999)"
    [void][Native.WinMM]::mciSendString("open `"$path`" type waveaudio alias $alias", $null, 0, [IntPtr]::Zero)
    [void][Native.WinMM]::mciSendString("play $alias wait", $null, 0, [IntPtr]::Zero)
    [void][Native.WinMM]::mciSendString("close $alias", $null, 0, [IntPtr]::Zero)
}

function Invoke-SystemSpeechFallback([string]$t) {
    Add-Type -AssemblyName System.Speech
    $s = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $s.Rate = 1
    $s.Volume = 100
    $s.Speak($t)
}

function New-WavFromPcm([byte[]]$pcm, [int]$sampleRate = 24000, [int]$channels = 1, [int]$bitsPerSample = 16) {
    $blockAlign = [int]($channels * ($bitsPerSample / 8))
    $byteRate = $sampleRate * $blockAlign
    $dataSize = $pcm.Length
    $ms = New-Object System.IO.MemoryStream
    $bw = New-Object System.IO.BinaryWriter $ms
    $bw.Write([Text.Encoding]::ASCII.GetBytes('RIFF'))
    $bw.Write([int](36 + $dataSize))
    $bw.Write([Text.Encoding]::ASCII.GetBytes('WAVE'))
    $bw.Write([Text.Encoding]::ASCII.GetBytes('fmt '))
    $bw.Write([int]16)
    $bw.Write([int16]1) # PCM
    $bw.Write([int16]$channels)
    $bw.Write([int]$sampleRate)
    $bw.Write([int]$byteRate)
    $bw.Write([int16]$blockAlign)
    $bw.Write([int16]$bitsPerSample)
    $bw.Write([Text.Encoding]::ASCII.GetBytes('data'))
    $bw.Write([int]$dataSize)
    $bw.Write($pcm)
    $bw.Flush()
    return $ms.ToArray()
}

function Invoke-AiTtsRest {
    param(
        [string]$Text,
        [string]$Voice,
        [string]$Language,
        [double]$Speed,
        [string]$ApiKey
    )

    $wav = [System.IO.Path]::Combine($env:TEMP, "ai-tts-rest-$PID-$(Get-Random).wav")
    try {
        $body = @{
            text          = $Text
            voice_id      = $Voice
            language      = $Language
            speed         = $Speed
            output_format = @{ codec = 'wav'; sample_rate = 24000 }
        } | ConvertTo-Json -Depth 5

        Invoke-WebRequest -Uri 'https://api.x.ai/v1/tts' `
            -Method Post `
            -Headers @{ Authorization = "Bearer $ApiKey" } `
            -ContentType 'application/json' `
            -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) `
            -OutFile $wav `
            -UseBasicParsing | Out-Null

        if (-not (Test-Path $wav) -or (Get-Item $wav).Length -eq 0) {
            throw 'xAI REST TTS returned no audio.'
        }
        Play-WavFile $wav
    }
    finally {
        Remove-Item $wav -ErrorAction SilentlyContinue
    }
}

function Ensure-ClientWebSocketTypes {
    # ClientWebSocket is in System.Net.WebSockets (available on modern Windows PowerShell 5.1+ / .NET)
    Add-Type -AssemblyName System.Net.Http -ErrorAction SilentlyContinue | Out-Null
}

function Invoke-AiTtsStreaming {
    param(
        [string]$Text,
        [string]$Voice,
        [string]$Language,
        [double]$Speed,
        [string]$ApiKey,
        [int]$OptimizeStreamingLatency = 2,
        [int]$SampleRate = 24000,
        [System.Net.WebSockets.ClientWebSocket]$ExistingSocket = $null,
        [switch]$KeepSocketOpen
    )

    Ensure-ClientWebSocketTypes

    $qs = "language=$([uri]::EscapeDataString($Language))" +
          "&voice=$([uri]::EscapeDataString($Voice))" +
          "&codec=pcm" +
          "&sample_rate=$SampleRate" +
          "&speed=$Speed" +
          "&optimize_streaming_latency=$OptimizeStreamingLatency"
    $uri = [Uri]"wss://api.x.ai/v1/tts?$qs"

    $ws = $ExistingSocket
    $created = $false
    if (-not $ws -or $ws.State -ne [System.Net.WebSockets.WebSocketState]::Open) {
        $ws = New-Object System.Net.WebSockets.ClientWebSocket
        $ws.Options.SetRequestHeader('Authorization', "Bearer $ApiKey")
        $cts = New-Object System.Threading.CancellationTokenSource
        $cts.CancelAfter([TimeSpan]::FromSeconds(60))
        $ws.ConnectAsync($uri, $cts.Token).GetAwaiter().GetResult() | Out-Null
        $created = $true
    }

    $pcm = New-Object System.IO.MemoryStream
    try {
        $sendCts = New-Object System.Threading.CancellationTokenSource
        $sendCts.CancelAfter([TimeSpan]::FromSeconds(30))

        $deltaMsg = (@{ type = 'text.delta'; delta = $Text } | ConvertTo-Json -Compress)
        $doneMsg = (@{ type = 'text.done' } | ConvertTo-Json -Compress)
        $deltaBytes = [Text.Encoding]::UTF8.GetBytes($deltaMsg)
        $doneBytes = [Text.Encoding]::UTF8.GetBytes($doneMsg)
        $ws.SendAsync((New-Object ArraySegment[byte] -ArgumentList @(, $deltaBytes)), [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $sendCts.Token).GetAwaiter().GetResult() | Out-Null
        $ws.SendAsync((New-Object ArraySegment[byte] -ArgumentList @(, $doneBytes)), [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $sendCts.Token).GetAwaiter().GetResult() | Out-Null

        $buffer = New-Object byte[] 65536
        $recvCts = New-Object System.Threading.CancellationTokenSource
        $recvCts.CancelAfter([TimeSpan]::FromSeconds(120))

        while ($true) {
            $ms = New-Object System.IO.MemoryStream
            $end = $false
            do {
                $seg = New-Object ArraySegment[byte] -ArgumentList @(, $buffer)
                $result = $ws.ReceiveAsync($seg, $recvCts.Token).GetAwaiter().GetResult()
                if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
                    throw 'WebSocket closed by server before audio.done'
                }
                $ms.Write($buffer, 0, $result.Count)
                $end = $result.EndOfMessage
            } while (-not $end)

            $jsonText = [Text.Encoding]::UTF8.GetString($ms.ToArray())
            $event = $jsonText | ConvertFrom-Json
            switch ($event.type) {
                'audio.delta' {
                    if ($event.delta) {
                        $chunk = [Convert]::FromBase64String([string]$event.delta)
                        $pcm.Write($chunk, 0, $chunk.Length)
                    }
                }
                'audio.done' { break }
                'error' { throw "TTS stream error: $($event.message)" }
                default { }
            }
            if ($event.type -eq 'audio.done') { break }
        }

        if ($pcm.Length -eq 0) { throw 'Streaming TTS returned no audio.' }

        $wavBytes = New-WavFromPcm -pcm $pcm.ToArray() -sampleRate $SampleRate
        $wavPath = [System.IO.Path]::Combine($env:TEMP, "ai-tts-ws-$PID-$(Get-Random).wav")
        try {
            [System.IO.File]::WriteAllBytes($wavPath, $wavBytes)
            Play-WavFile $wavPath
        }
        finally {
            Remove-Item $wavPath -ErrorAction SilentlyContinue
        }

        if ($KeepSocketOpen -or (-not $created)) {
            return $ws
        }
        return $null
    }
    catch {
        if ($ws -and $ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
            try { $ws.Abort() } catch {}
        }
        throw
    }
    finally {
        if (-not $KeepSocketOpen -and $created -and $ws) {
            try {
                if ($ws.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
                    $ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, 'done', [Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
                }
            } catch {}
            try { $ws.Dispose() } catch {}
        }
        $pcm.Dispose()
    }
}

function Invoke-AiTtsSpeak {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [string]$Voice = 'carina',
        [string]$Language = 'en',
        [double]$Speed = 1.0,
        [int]$OptimizeStreamingLatency = 2,
        [int]$SampleRate = 24000,
        [ValidateSet('auto', 'stream', 'rest')][string]$Transport = 'auto',
        [System.Net.WebSockets.ClientWebSocket]$ExistingSocket = $null,
        [switch]$KeepSocketOpen
    )

    $key = Get-AiTtsApiKey
    if (-not $key) {
        Write-Warning 'XAI_API_KEY not set; using built-in System.Speech.'
        Invoke-SystemSpeechFallback $Text
        return $null
    }

    if ($Transport -eq 'rest') {
        Invoke-AiTtsRest -Text $Text -Voice $Voice -Language $Language -Speed $Speed -ApiKey $key
        return $null
    }

    try {
        return Invoke-AiTtsStreaming `
            -Text $Text -Voice $Voice -Language $Language -Speed $Speed -ApiKey $key `
            -OptimizeStreamingLatency $OptimizeStreamingLatency -SampleRate $SampleRate `
            -ExistingSocket $ExistingSocket -KeepSocketOpen:$KeepSocketOpen
    }
    catch {
        if ($Transport -eq 'stream') { throw }
        Write-Warning "Streaming TTS failed ($($_.Exception.Message)); falling back to REST."
        Invoke-AiTtsRest -Text $Text -Voice $Voice -Language $Language -Speed $Speed -ApiKey $key
        return $null
    }
}
