@echo off
setlocal enabledelayedexpansion

title PDF Editor - Native Extensions Builder

set "SCRIPT_DIR=%~dp0"
set "LIBS_DIR=%SCRIPT_DIR%libs"

echo =============================================
echo   PDF Editor - Native Extensions Builder
echo =============================================
echo.

where wsl >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] WSL not found.
    echo.
    echo Please install WSL:
    echo   wsl --install
    echo.
    echo Or install Ubuntu from the Microsoft Store.
    goto :error
)

echo [INFO] WSL detected.

wsl --list --verbose 2>nul | findstr /i "Ubuntu" >nul
if %ERRORLEVEL% neq 0 (
    echo [WARN] Ubuntu not found in WSL distributions.
    echo [INFO] Attempting to use default WSL distribution.
)

echo [INFO] Starting build in WSL...
echo.

wsl -e bash -c "chmod +x '%SCRIPT_DIR%build.sh' 2>/dev/null; cd '%SCRIPT_DIR%' && bash build.sh"
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] WSL build failed.
    goto :error
)

echo.
echo [INFO] Checking for built libraries...

if not exist "%LIBS_DIR%" (
    mkdir "%LIBS_DIR%"
)

dir /b "%LIBS_DIR%\*.so" 2>nul >nul
if %ERRORLEVEL% neq 0 (
    echo [WARN] No .so files found in libs directory.
    echo [INFO] Attempting to copy from WSL filesystem...
)

echo.
echo =============================================
echo   Build Complete
echo =============================================
echo.

set "LIB_LIST=pdf_renderer pdf_search_engine pdf_compressor pdf_ocr_preprocess pdf_crypto pdf_export"

for %%L in (%LIB_LIST%) do (
    if exist "%LIBS_DIR%\lib%%L.so" (
        echo   [OK] lib%%L.so
    ) else (
        echo   [--] lib%%L.so (not built)
    )
)

echo.
echo Usage from Python (via WSL):
echo.
echo   import subprocess
echo   result = subprocess.run(['wsl', 'bash', '-c', ^<path-to-script^>], capture_output=True)
echo.
echo   Or mount the libs directory in WSL:
echo   wsl bash -c "export LD_LIBRARY_PATH=/mnt/d/pdf_editor/native/libs:$LD_LIBRARY_PATH"
echo.
echo =============================================

goto :done

:error
echo.
echo [ERROR] Build failed. Check the output above.
exit /b 1

:done
endlocal
exit /b 0
