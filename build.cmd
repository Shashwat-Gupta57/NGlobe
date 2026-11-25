@echo off
rem Builds dist\NGlobe.exe - one file, double-click to run. Needs Python 3.10+ and Node.js.
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

rem Resources land where nglobe.utils.resource_path expects them (relative to the bundle root)
.venv\Scripts\pyinstaller --noconfirm --clean --onefile --console --name NGlobe --icon icon.png ^
    --paths src ^
    --collect-all mitmproxy ^
    --collect-submodules uvicorn ^
    --add-data "src\nglobe\ui;ui" ^
    --add-data "src\nglobe\geoip\data;geoip\data" ^
    --add-data "src\nglobe\config.toml;." ^
    src\nglobe\__main__.py || goto :fail

echo.
echo Built dist\NGlobe.exe
exit /b 0

:fail
echo.
echo Build failed.
pause
exit /b 1
