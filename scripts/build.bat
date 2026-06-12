@echo off
setlocal

cd /d "%~dp0"
cd ..
set "PROJECT_ROOT=%cd%"
set "BUILD_ROOT=%PROJECT_ROOT%\build\win"
set "RELEASE_DIR=%PROJECT_ROOT%\build\release\tcp_debug-win"
set "ARTIFACTS_DIR=%PROJECT_ROOT%\build\artifacts\tcp_debug-win"

echo [1/6] Checking build environment...
where python >nul 2>nul
if errorlevel 1 (
    echo Python not found. Please install Python or activate a conda environment first.
    goto :error
)
where npm >nul 2>nul
if errorlevel 1 (
    echo npm not found. Please install Node.js first.
    goto :error
)

if "%CONDA_PREFIX%"=="" (
    echo Conda environment is not active. Using current Python and pip.
) else (
    echo Using conda environment: %CONDA_PREFIX%
)

echo [2/6] Installing Python dependencies...
python -m pip install --upgrade pip
if errorlevel 1 goto :error
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :error

echo [3/6] Building Vue frontend...
call npm install
if errorlevel 1 goto :error
call npm run build
if errorlevel 1 goto :error

echo [4/6] Building tcp_debug.exe...
tasklist /FI "IMAGENAME eq tcp_debug.exe" 2>nul | find /I "tcp_debug.exe" >nul
if not errorlevel 1 (
    echo tcp_debug.exe is running. Please close it before building.
    goto :error
)

python -m PyInstaller ^
    --clean ^
    --noconfirm ^
    --onefile ^
    --name tcp_debug ^
    --icon "%PROJECT_ROOT%\assets\icon.ico" ^
    --distpath "%BUILD_ROOT%" ^
    --workpath "%BUILD_ROOT%\temp" ^
    --specpath "%BUILD_ROOT%" ^
    --add-data "%PROJECT_ROOT%\src\dist;dist" ^
    --add-data "%PROJECT_ROOT%\src\json;json" ^
    --add-data "%PROJECT_ROOT%\assets\icon.ico;assets" ^
    "%PROJECT_ROOT%\src\server.py"
if errorlevel 1 goto :error

echo [5/6] Creating portable release directory...
if exist "%RELEASE_DIR%" rmdir /s /q "%RELEASE_DIR%"
if exist "%ARTIFACTS_DIR%" rmdir /s /q "%ARTIFACTS_DIR%"
mkdir "%RELEASE_DIR%"
mkdir "%ARTIFACTS_DIR%"
mkdir "%ARTIFACTS_DIR%\resources"
mkdir "%ARTIFACTS_DIR%\python-deps"
copy /y "%BUILD_ROOT%\tcp_debug.exe" "%RELEASE_DIR%\tcp_debug.exe" >nul
copy /y "%PROJECT_ROOT%\requirements.txt" "%ARTIFACTS_DIR%\requirements.txt" >nul
copy /y "%PROJECT_ROOT%\package.json" "%ARTIFACTS_DIR%\package.json" >nul
if exist "%PROJECT_ROOT%\package-lock.json" copy /y "%PROJECT_ROOT%\package-lock.json" "%ARTIFACTS_DIR%\package-lock.json" >nul
xcopy /e /i /y "%PROJECT_ROOT%\src\json" "%ARTIFACTS_DIR%\resources\json" >nul
xcopy /e /i /y "%PROJECT_ROOT%\src\dist" "%ARTIFACTS_DIR%\resources\dist" >nul
python -m pip download -r requirements.txt -d "%ARTIFACTS_DIR%\python-deps"
if errorlevel 1 goto :error
(
  echo @echo off
  echo cd /d "%%~dp0"
  echo tcp_debug.exe
) > "%RELEASE_DIR%\start.bat"
(
  echo tcp_debug Windows portable release
  echo.
  echo Start: double click start.bat or run tcp_debug.exe
  echo HTTP: http://127.0.0.1:8080
  echo Vue frontend is built into tcp_debug.exe. Do not run npm or Vue separately.
  echo Note: Linux netplan network apply is not supported by this Windows build.
  echo Debug materials are in build\artifacts\tcp_debug-win on the build machine.
) > "%RELEASE_DIR%\README.txt"

echo [6/6] Cleaning temporary build files...
if exist "%BUILD_ROOT%\temp" rmdir /s /q "%BUILD_ROOT%\temp"
if exist "%BUILD_ROOT%\tcp_debug.spec" del /q "%BUILD_ROOT%\tcp_debug.spec"
if exist "__pycache__" rmdir /s /q "__pycache__"

echo Build finished.
echo Output: %RELEASE_DIR%
exit /b 0

:error
echo Build failed.
exit /b 1
