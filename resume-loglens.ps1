# Resume LogLens development environment

Write-Host "Starting LogLens Docker services..."
docker compose up -d

Write-Host ""
Write-Host "Activating Python virtual environment..."
.\.venv\Scripts\Activate.ps1

Write-Host ""
Write-Host "Checking Docker services..."
docker compose ps

Write-Host ""
Write-Host "LogLens resumed."