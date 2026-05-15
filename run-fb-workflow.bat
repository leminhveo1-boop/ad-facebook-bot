@echo off
chcp 65001 > nul
echo ============================================================
echo  FB ADS AUTO-WORKFLOW - Dang chay...
echo  Time: %DATE% %TIME%
echo ============================================================

:: -- CAU HINH -- PASTE TOKEN VAO DAY ----------------------
set FB_ACCESS_TOKEN=EAAWretZAkV04BRQp9Gtoti6ZCHx3nGiB8eN2XKN9oxmpimFNSCvzEKM5p8WP9YZAIQKaRkcxZCG3PyKod9Xh6VhO9EuTRtrnMIcCti9eGLJrDnXC2aSVIXXGpwCaKViL1b0WTIQ3gqcNSCXCsx3uql6VfOVDqVPMFCj3ccSrbPsIXWfYZCWgR6gHukKkA8Abks0ezch9r0k0B7fUrNPWyY9fARLCBRiZB7PUtzKtiQ5iUUIxZAF3y5h5YaH8c8DoYlVsUZC5f6lI0ULnHW41hla1dAZDZD
set FB_AD_ACCOUNT_ID=act_2087249431632156
set FB_APP_ID=1595918954813262
set PYTHONIOENCODING=utf-8

:: -- CHAY WORKFLOW ----------------------------------------
python "f:\Antigravity\brain2\vault\Projects\ad-facebook\fb-workflow.py"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] Workflow hoan thanh. Dang gui bao cao qua Telegram...
    python "f:\Antigravity\brain2\vault\Projects\ad-facebook\fb-telegram-report.py"
) else (
    echo.
    echo [ERROR] Co loi xay ra. Kiem tra logs/ de biet chi tiet.
)

echo ============================================================
echo  Ket thuc: %DATE% %TIME%
echo ============================================================
