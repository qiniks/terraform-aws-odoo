@echo off
setlocal enabledelayedexpansion

:: Configuration
set "CLOUDFRONT_DOMAIN=d15khkzf03z20p.cloudfront.net"
set "ODOO_DB=odoo"
set "SECRET_ID=odoo-root-user"

:: Step 1: Retrieve secret from AWS Secrets Manager
for /f "tokens=*" %%a in ('aws secretsmanager get-secret-value --secret-id %SECRET_ID% --query SecretString --output text') do (
    set "SECRET_JSON=%%a"
)

if %ERRORLEVEL% neq 0 (
    echo Failed to retrieve secret from AWS Secrets Manager
    exit /b 1
) else (
    echo Successfully retrieved secret from AWS Secrets Manager
)

echo !SECRET_JSON!

