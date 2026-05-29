# Youyuzz Switch Plugin

Switch homebrew plugin for game batch search, cloud disk download, and DBI installation.

## Tech Stack
- C/C++ (C++17)
- devkitPro + libnx
- SDL2 (GUI)
- libcurl (HTTP/networking)

## Project Structure
```
switch-plugin/
  Makefile               # devkitPro build file
  include/
    youyuzz_common.h     # Shared types, constants, colors
  src/
    main.cpp             # Entry point (socketInit, SDL init)
    app/
      app_state.h        # AppState enum (MENU, SEARCH, DETAIL, INSTALL, ACTIVATE, SETTINGS)
      app.h / app.cpp    # Main app controller (state machine, input, render loop)
    gui/
      gui.h / gui.cpp    # SDL2 rendering (draw_rect, draw_text, progress_bar, swkbd)
    net/
      http_client.h/cpp  # libcurl wrapper (GET, POST, download with progress, SSE listener)
      api_client.h/cpp   # PC backend API (search, detail, install) + CF Workers (activate, verify)
    auth/
      auth.h / auth.cpp  # Activation logic (free tries, license key, device ID)
    config/
      config.h / config.cpp  # Config load/save from sdmc:/youyuzz/config.json
```

## Architecture
- **Light Client Mode**: Switch connects to PC backend (FastAPI on port 18888) for search/download/install
- **Direct Mode**: Switch calls Cloudflare Workers API directly for activation verification
- **Offline**: Cached activation status used when no network

## Features
1. **Game Search**: Virtual keyboard input -> PC backend search -> result list
2. **Game Detail**: View game info (main, update, DLC, cheat links)
3. **Install**: Trigger install via PC backend -> SSE real-time progress
4. **Activation**: Enter activation code (XXXX-XXXX-XXXX) -> CF Workers verify
5. **Free Tries**: 5 free installs before activation required
6. **Settings**: Configure PC server IP address

## Building
```bash
# Requires devkitPro with libnx, SDL2, libcurl installed
export DEVKITPRO=/opt/devkitpro  # or C:\devkitPro on Windows
cd switch-plugin
make
# Output: youyuzz-switch.nro
```

## Controls
- **D-Pad / Left Stick**: Navigate menus
- **A**: Select / Confirm
- **B**: Back / Cancel
- **+**: Exit app

## Configuration
Config file: `sdmc:/youyuzz/config.json`
- `pc_ip`: PC backend server IP (default: 192.168.1.100)
- `pc_port`: PC backend server port (default: 18888)
- `license_key`: Cached activation license key
- `activated`: Activation status
- `free_tries_used`: Number of free tries consumed

## API Endpoints Used
### PC Backend (http://<ip>:<port>)
- `GET /api/search?keyword=<text>` - Search games
- `GET /api/game/detail?url=<url>` - Get game detail
- `POST /api/install` - Start install task
- `GET /api/install/<id>/progress` - Poll progress
- `GET /api/install/<id>/stream` - SSE progress stream

### Cloudflare Workers
- `POST /api/auth/activate` - Activate license code
- `GET /api/auth/verify` - Verify license status