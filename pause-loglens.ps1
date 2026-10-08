# ============================================================
# LogLens - Pause Development Environment
# ============================================================

Write-Host ""
Write-Host "========================================"
Write-Host "       PAUSING LOG LENS"
Write-Host "========================================"
Write-Host ""

# ------------------------------------------------------------
# 1. Check Git status
# ------------------------------------------------------------

Write-Host "Checking Git status..."
git status --short

Write-Host ""

# ------------------------------------------------------------
# 2. Ask for commit message
# ------------------------------------------------------------

$commitMessage = Read-Host "Enter Git commit message"

if ([string]::IsNullOrWhiteSpace($commitMessage)) {
    Write-Host ""
    Write-Host "ERROR: Commit message cannot be empty." -ForegroundColor Red
    Write-Host "Pause cancelled. No changes were committed."
    exit 1
}

# ------------------------------------------------------------
# 3. Stage all changes
# ------------------------------------------------------------

Write-Host ""
Write-Host "Staging changes..."

git add .

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Git add failed." -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------
# 4. Commit changes
# ------------------------------------------------------------

Write-Host "Creating Git commit..."

git commit -m "$commitMessage"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ERROR: Git commit failed." -ForegroundColor Red
    Write-Host "Docker services were NOT stopped."
    exit 1
}

# ------------------------------------------------------------
# 5. Stop Docker services
# ------------------------------------------------------------

Write-Host ""
Write-Host "Stopping LogLens Docker services..."

docker compose stop

if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: Docker services could not be stopped." -ForegroundColor Yellow
}
else {
    Write-Host "PostgreSQL and Redis stopped."
}

# ------------------------------------------------------------
# 6. Deactivate Python virtual environment
# ------------------------------------------------------------

Write-Host ""
Write-Host "Deactivating Python virtual environment..."

deactivate

# ------------------------------------------------------------
# 7. Final status
# ------------------------------------------------------------

Write-Host ""
Write-Host "========================================"
Write-Host "       LOG LENS PAUSED"
Write-Host "========================================"
Write-Host ""
Write-Host "Git commit created:"
Write-Host "  $commitMessage"
Write-Host ""
Write-Host "PostgreSQL and Redis are stopped."
Write-Host "PostgreSQL data is preserved."
Write-Host ".venv has been deactivated."
Write-Host ""
Write-Host "Now tell ChatGPT: pause"
Write-Host "It will provide:"
Write-Host "  1. Commit message"
Write-Host "  2. Work summary for your progress document"
Write-Host ""