@echo off
setlocal enabledelayedexpansion

:: Colors for output (Only works with ANSI-enabled terminals like Windows Terminal)
set "GREEN=[92m"
set "YELLOW=[93m"
set "RED=[91m"
set "NC=[0m"
set "BLUE=[94m"

:: Configuration
set CLOUDFRONT_DOMAIN=d290mq7kqg95wg.cloudfront.net
set ODOO_DB=odoo
set SECRET_ID=odoo-root-user

:: Function to print step information
echo.
echo %YELLOW%==== Retrieving Odoo credentials from AWS Secrets Manager ==== %NC%

:: Step 1: Retrieve secret from AWS Secrets Manager
for /f "tokens=*" %%i in ('aws secretsmanager get-secret-value --secret-id %SECRET_ID% --query "SecretString" --output text') do set SECRET_JSON=%%i
if errorlevel 1 (
    echo %RED%✗ Failed to retrieve secret from AWS Secrets Manager%NC%
)
echo %GREEN%✓ Success%NC%

:: Step 2: Parse JSON to get username and password
for /f "tokens=*" %%i in ('echo %SECRET_JSON% ^| jq -r ".username"') do set USERNAME=%%i
for /f "tokens=*" %%i in ('echo %SECRET_JSON% ^| jq -r ".password"') do set PASSWORD=%%i

if "%USERNAME%"=="" (
    echo %RED%✗ Failed to parse username from secret%NC%

)
if "%PASSWORD%"=="" (
    echo %RED%✗ Failed to parse password from secret%NC%

)

:: Step 3: Display credentials
echo.
echo %YELLOW%==== Odoo Credentials ==== %NC%
echo %BLUE%HOST_URL=%NC%https://%CLOUDFRONT_DOMAIN%
echo %BLUE%DB_NAME=%NC%%ODOO_DB%
echo %BLUE%DB_USERNAME=%NC%%USERNAME%
echo %BLUE%DB_PASSWORD=%NC%%PASSWORD%

:: Step 4: Create a .env file (optional)
if "%1"=="--save" (
    echo.
    echo %YELLOW%==== Saving credentials to .env file ==== %NC%
    (
        echo HOST_URL=https://%CLOUDFRONT_DOMAIN%
        echo DB_NAME=%ODOO_DB%
        echo DB_USERNAME=%USERNAME%
        echo DB_PASSWORD=%PASSWORD%
    ) > .env.odoo
    echo %GREEN%✓ Credentials saved to .env.odoo file%NC%
    echo You can load these credentials with: "set /p < .env.odoo"
)

echo.
echo %GREEN%Script completed successfully!%NC%
echo You can use these credentials to access your Odoo instance.

echo.
echo %YELLOW%Press any key to exit...%NC%
pause > nul

endlocal
