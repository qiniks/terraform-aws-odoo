@echo off
setlocal enabledelayedexpansion

:: Configuration
set CLUSTER_NAME=odoo
set SERVICE_NAME=odoo
set DATASYNC_TASK_ARN=arn:aws:datasync:us-east-1:021776651623:task/task-0c1406bd155b1aaf7
set S3_BUCKET=odoo-odoo-custom-121312
set CLOUDFRONT_DOMAIN=dodm7d5gantcd.cloudfront.net
set ODOO_DB=odoo

:: Check if a module name was provided
if "%~1"=="" (
    echo Usage: %0 ^<module_name^>
    echo Example: %0 lead_pool
    exit /b 1
)

set MODULE_NAME=%~1

:: Step 1: Check if module exists in S3
echo.
echo ==== Checking if module exists in S3 ====
aws s3 ls s3://%S3_BUCKET%/modules/%MODULE_NAME%/ --recursive
if %ERRORLEVEL% neq 0 (
    echo Module %MODULE_NAME% not found in S3 bucket
    exit /b 1
) else (
    echo Module %MODULE_NAME% found in S3
)

:: Step 2: Start DataSync task
echo.
echo ==== Starting DataSync to copy module files to EFS ====
for /f "tokens=*" %%i in ('aws datasync start-task-execution --task-arn %DATASYNC_TASK_ARN% --query "TaskExecutionArn" --output text') do set EXECUTION_ARN=%%i
if %ERRORLEVEL% neq 0 (
    echo Failed
    exit /b 1
) else (
    echo Success
)
echo DataSync execution ARN: %EXECUTION_ARN%

:: Step 3: Wait for DataSync to complete
echo.
echo ==== Waiting for DataSync task to complete ====
set STATUS=LAUNCHING
:datasync_loop
echo DataSync status: !STATUS!
timeout /t 10 /nobreak >nul
for /f "tokens=*" %%i in ('aws datasync describe-task-execution --task-execution-arn !EXECUTION_ARN! --query "Status" --output text') do set STATUS=%%i
if "!STATUS!"=="ERROR" (
    echo DataSync task failed
    exit /b 1
)
if not "!STATUS!"=="SUCCESS" goto datasync_loop
echo DataSync completed successfully

:: Step 4: Force new deployment of the ECS service
echo.
echo ==== Restarting Odoo service to pick up new module ====
aws ecs update-service --cluster %CLUSTER_NAME% --service %SERVICE_NAME% --force-new-deployment >nul
if %ERRORLEVEL% neq 0 (
    echo Failed
    exit /b 1
) else (
    echo Success
)

:: Step 5: Wait for ECS service to stabilize
echo.
echo ==== Waiting for ECS service to stabilize ====
aws ecs wait services-stable --cluster %CLUSTER_NAME% --services %SERVICE_NAME%
if %ERRORLEVEL% neq 0 (
    echo Failed
    exit /b 1
) else (
    echo Success
)

:: Step 6: Provide instructions for updating app list in Odoo
echo.
echo ==== Next steps ====
echo 1. Wait 1-2 minutes for Odoo to fully start
echo 2. Log in to Odoo at https://%CLOUDFRONT_DOMAIN% with your credentials
echo 3. Go to Apps menu
echo 4. Remove the 'Apps' filter
echo 5. Click on 'Update Apps List' in the top menu
echo 6. Search for '%MODULE_NAME%'
echo 7. Install the module

echo.
echo Script completed successfully!
echo Your module %MODULE_NAME% should now be available in Odoo.