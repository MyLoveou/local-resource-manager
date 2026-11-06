param(
  [string]$Root = "D:\Project\ai",
  [string]$Model = "qwen2.5vl:3b"
)

$ErrorActionPreference = "Stop"
$ollamaDir = Join-Path $Root "ollama"
$modelsDir = Join-Path $Root "models"
$ollamaHome = Join-Path $Root "ollama-home"
$zip = Join-Path $Root "ollama-windows-amd64.zip"
$url = "https://github.com/ollama/ollama/releases/download/v0.40.9/ollama-windows-amd64.zip"

New-Item -ItemType Directory -Force $Root, $modelsDir, $ollamaHome | Out-Null

if (-not (Test-Path (Join-Path $ollamaDir "ollama.exe"))) {
  if (-not (Test-Path $zip)) {
    Write-Host "Downloading Ollama to $zip"
    Invoke-WebRequest -UseBasicParsing -OutFile $zip $url
  }
  Expand-Archive -LiteralPath $zip -DestinationPath $ollamaDir -Force
}

$ollama = Join-Path $ollamaDir "ollama.exe"
$env:OLLAMA_HOST = "127.0.0.1:11434"
$env:OLLAMA_MODELS = $modelsDir
$env:OLLAMA_HOME = $ollamaHome

$running = $false
try {
  $response = Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:11434/api/tags" -TimeoutSec 2
  $running = $response.StatusCode -eq 200
} catch {
  $running = $false
}

if (-not $running) {
  Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
  Start-Sleep -Seconds 3
}

& $ollama pull $Model
Write-Host "Ollama: $ollama"
Write-Host "Models: $modelsDir"
Write-Host "Model:  $Model"
