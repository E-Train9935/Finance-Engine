$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "FINENGINE // bootstrapping local environment" -ForegroundColor Cyan

if (!(Test-Path ".venv")) {
  py -3 -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r apps\api\requirements.txt

if (!(Test-Path "apps\api\.env")) {
  Copy-Item apps\api\.env.example apps\api\.env
  Write-Host "Created apps/api/.env. Add your TWELVE_DATA_API_KEY for live price data." -ForegroundColor Yellow
}

Push-Location apps\web
npm install
Pop-Location

$api = Start-Process powershell -PassThru -ArgumentList "-NoExit", "-Command", "cd '$Root'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --reload"
Write-Host "API process: $($api.Id)" -ForegroundColor DarkGray
Start-Sleep -Seconds 2

Set-Location apps\web
npm run dev
