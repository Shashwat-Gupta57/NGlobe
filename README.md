# 🌐 NetworkGlobe

**Real-time MITM proxy visualization platform.** Intercepts outbound HTTPS traffic, resolves geolocations, and renders every connection as an animated arc on an interactive world map.

*GlassWire meets FlightRadar24 — but for your network requests.*

---

## Quick Start

### 1. Backend Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install --trusted-host pypi.org -r requirements.txt
```

### 2. GeoIP Databases (Optional but Recommended)

NetworkGlobe uses MaxMind GeoLite2 databases for geographic resolution.

```bash
# Create a free MaxMind account: https://www.maxmind.com/en/geolite2/signup
# Generate a license key, then:

python -m backend.geoip.download --license-key YOUR_LICENSE_KEY
```

Without GeoIP databases, requests are still captured but won't show map arcs.

### 3. Start the Backend

```bash
python main.py
```

The server starts at **http://127.0.0.1:8085** with the dashboard.

### 4. Frontend Development (Optional)

For live frontend development with hot reload:

```bash
cd frontend
npm install
npm run dev       # http://localhost:5173 → proxied to backend
```

### 5. Configure Your Browser

Set your browser's HTTP proxy to `127.0.0.1:8888` to route traffic through NetworkGlobe.

> **Note:** You'll need to trust the mitmproxy CA certificate for HTTPS interception.
> The certificate is auto-generated at `~/.networkglobe/certs/` on first launch.

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│  Browser    │────▶│  mitmproxy   │────▶│  CaptureAddon│
│  (proxy)    │     │  :8888       │     │  (extractor) │
└─────────────┘     └──────────────┘     └──────┬───────┘
                                                │ RawFlowEvent
                                                ▼
                                        ┌──────────────┐
                                        │ EventPipeline│
                                        │ + GeoIP      │
                                        └──────┬───────┘
                                               │ NetworkEvent
                                               ▼
                                        ┌──────────────┐
                                        │   EventBus   │
                                        └──┬────────┬──┘
                                           │        │
                              ┌────────────┘        └────────────┐
                              ▼                                  ▼
                      ┌──────────────┐                   ┌──────────────┐
                      │ BatchWriter  │                   │ WebSocket    │
                      │ (SQLite)     │                   │ Manager      │
                      └──────────────┘                   └──────┬───────┘
                                                                │ JSON
                                                                ▼
                                                        ┌──────────────┐
                                                        │ React + Map  │
                                                        │ Dashboard    │
                                                        └──────────────┘
```

## Configuration

Edit `backend/config.toml` to customize:

| Section        | Key                | Default       | Description                     |
|----------------|--------------------|--------------:|---------------------------------|
| `proxy`        | `listen_port`      | `8888`        | Proxy listen port               |
| `server`       | `port`             | `8085`        | Dashboard server port           |
| `geoip`        | `cache_size`       | `10000`       | IP lookup LRU cache size        |
| `animations`   | `max_visible_arcs` | `500`         | Max arcs rendered on map        |
| `performance`  | `pipeline_batch_size`| `50`        | DB write batch size             |
| `capture`      | `ignored_hosts`    | `[localhost]` | Hosts to skip capturing         |

## Tech Stack

| Layer      | Technology                                  |
|------------|---------------------------------------------|
| Proxy      | mitmproxy 11                                |
| Backend    | Python 3.13, FastAPI, Uvicorn, aiosqlite    |
| Database   | SQLite (WAL mode, batched writes)           |
| GeoIP      | MaxMind GeoLite2 + maxminddb                |
| Frontend   | React 19, TypeScript, Vite                  |
| Styling    | TailwindCSS v4, Framer Motion               |
| Map        | MapLibre GL JS + deck.gl (ArcLayer)         |
| Charts     | Recharts                                    |
| State      | Zustand                                     |

## License

MIT
