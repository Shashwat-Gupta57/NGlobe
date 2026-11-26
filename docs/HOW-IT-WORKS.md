# How NGlobe works

The longer version of the README: what runs where, what gets stored, and how to fix things.

## The pieces

| Piece | Where | Job |
|---|---|---|
| `NGlobe.exe` | `%LOCALAPPDATA%\Programs\NGlobe` | The app: a local web server (FastAPI) plus an embedded mitmproxy |
| `unins.exe` | same folder | A renamed copy of `NGlobe.exe`; that name makes it run the uninstall flow |
| Web UI | served by `NGlobe.exe` at `http://127.0.0.1:8085` | React + deck.gl globe, opened in your default browser |
| Data | `%USERPROFILE%\.nglobe\` | `data\` history database, `logs\`, `certs\` (your CA), `geoip\` (optional fresher databases) |

### Startup sequence

1. If a previous run crashed while the Windows proxy pointed at NGlobe, the original settings are restored first.
2. NGlobe checks whether its own certificate is trusted, which decides whether browser HTTPS is decrypted.
3. The database and GeoIP databases are opened. GeoIP uses `~/.nglobe/geoip` if present, otherwise the bundled copy.
4. mitmproxy starts on `127.0.0.1:8888` (or any free port if that one is taken) and the Windows proxy is pointed at it.
   The original settings are saved to `~/.nglobe/proxy_backup.json` *before* anything changes.
5. NGlobe asks Windows to start mitmproxy's *local mode* redirector (one UAC prompt). If you accept, every app is
   captured. If you decline, only browsers are.
6. Your browser opens on the globe.

On exit (closing the console window, Ctrl+C, or a normal shutdown) the proxy settings are restored. If NGlobe
is killed, the next launch or the uninstaller restores them.

## Capture modes

| Traffic | How it arrives | Decrypted? | What you see |
|---|---|---|---|
| Browsers, HTTPS details **on** | Windows proxy | Yes | Every request: method, path, status, size, latency |
| Browsers, HTTPS details **off** | Windows proxy | No | Every connection: host, IP, location, bytes |
| Apps that pin certificates | Windows proxy | No (automatic fallback) | Every connection |
| Everything else | Local mode (WinDivert) | **Never** | Every connection: hostname (from DNS or TLS SNI), IP, location, bytes |
| Plain `http://` | Either | Not needed | Every request |

Connections that aren't decrypted show up on the globe as soon as data starts flowing. Their byte counts are
saved when they close, so the *Traffic* total and history fill in a little later than the live arcs.

## The certificate

- Created on first launch, unique to your PC: `~/.nglobe/certs/mitmproxy-ca-cert.pem`, issuer **"NGlobe"**.
  The private key never leaves that folder.
- Clicking *HTTPS details: off* installs it into your **user** trust store (`certutil -user -addstore Root`).
  Windows shows a confirmation and no admin is needed.
- Clicking *HTTPS details: on* removes it again (`certutil -user -delstore Root`). Uninstalling also removes it.
- Chrome and Edge use the Windows store. Firefox 120+ does too. Older Firefox needs
  `security.enterprise_roots.enabled = true`.

## Storage and memory

- About 150 MB on disk, half of which is the city-level GeoIP database.
- About 100 MB of RAM while running. The GeoIP databases are memory-mapped, so Windows only loads the parts
  that get used. The live list in the UI keeps the latest 1,000 connections.
- History grows with use, typically a few MB per hour of browsing. The *History* button shows the size and wipes it.

## Configuration

Everything has a sensible default. To change something, create `%USERPROFILE%\.nglobe\config.toml`:

```toml
[proxy]
listen_port = 8888          # any free port is used if this one is taken
set_system_proxy = true     # false: point apps at 127.0.0.1:<port> yourself

[server]
port = 8085                 # web UI
open_browser_on_start = true

[capture]
all_apps = true             # false: browsers only, no admin prompt
ignored_hosts = ["localhost", "127.0.0.1", "::1"]

[location]
auto_detect = true          # false: use latitude/longitude below
latitude = 0.0
longitude = 0.0
```

Environment variables work too: `NETWORKGLOBE_<SECTION>__<KEY>`, e.g. `NETWORKGLOBE_CAPTURE__ALL_APPS=false`.

## Building

`build.cmd` does everything:

1. Creates `.venv` and installs the package, PyInstaller and Pillow.
2. Builds the UI (`frontend/`) straight into `src/nglobe/ui`.
3. Builds the app as a folder (`build\app\NGlobe`), so it starts in about 2 s with nothing to unpack.
4. Zips that folder and wraps it into the installer, `dist\NGlobe-Setup.exe` (`installer/setup.py`, plain Tk).

Publishing a GitHub release runs the same build on GitHub's Windows runners and attaches the installer to the release.

Tests: `pytest -q tests`. Lint: `ruff check src/nglobe`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| No internet after NGlobe was killed | Start NGlobe again (it restores the proxy on launch) or run `unins.exe`. Manual fix: *Settings → Network → Proxy → turn off "Use a proxy server"*. |
| Only "Browsers only" | The admin prompt was declined, or another tool is using WinDivert. Restart NGlobe and accept the prompt. |
| A site breaks with HTTPS details on | Click *HTTPS details: on* to turn it off. Pinned apps are switched to pass-through automatically. |
| Port already in use | NGlobe picks another free port automatically. If the web UI port is taken by something else, set `[server] port`. |
| Logs | `%USERPROFILE%\.nglobe\logs\networkglobe.log` |
