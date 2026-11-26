@echo off
rem Builds dist\NGlobe-Setup.exe (the installer). Needs Python 3.10+ and Node.js.
setlocal
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    py -3 -m venv .venv || goto :fail
)
.venv\Scripts\python -m pip install -q -e . pyinstaller pillow || goto :fail

pushd frontend
call npm ci || (popd & goto :fail)
call npm run build || (popd & goto :fail)
popd

rem 1) The app, as a folder (starts fast: nothing to unpack on each launch).
rem    Resources land where nglobe.utils.resource_path expects them (relative to _internal).
.venv\Scripts\pyinstaller --noconfirm --clean --onedir --console --name NGlobe --icon icon.png ^
    --distpath build\app --workpath build\work ^
    --paths src ^
    --collect-all mitmproxy ^
    --collect-all mitmproxy_windows ^
    --collect-submodules uvicorn ^
    --add-data "src\nglobe\ui;ui" ^
    --add-data "src\nglobe\geoip\data;geoip\data" ^
    --add-data "src\nglobe\config.toml;." ^
    src\nglobe\__main__.py || goto :fail

rem 2) Zip it as the installer's payload
.venv\Scripts\python -c "import shutil; shutil.make_archive('build/payload', 'zip', 'build/app/NGlobe')" || goto :fail

rem 3) The installer: one windowed exe carrying the payload
.venv\Scripts\pyinstaller --noconfirm --clean --onefile --windowed --name NGlobe-Setup --icon icon.png ^
    --distpath dist --workpath build\work-setup ^
    --paths src ^
    --add-data "build\payload.zip;." ^
    --add-data "icon.png;." ^
    --add-data "installer\logo.png;." ^
    installer\setup.py || goto :fail

echo.
echo Built dist\NGlobe-Setup.exe
exit /b 0

:fail
echo.
echo Build failed.
pause
exit /b 1
