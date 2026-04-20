# Functional Specification Document
# Workshop Inventory PWA

**Version:** 1.0
**Author:** TBD
**Date:** 2026-04-20
**Status:** Released — all phases complete and deployed

---

## Table of Contents

1. [Overview](#1-overview)
2. [Goals & Non-Goals](#2-goals--non-goals)
3. [Users & Access Control](#3-users--access-control)
4. [System Architecture](#4-system-architecture)
5. [Tech Stack](#5-tech-stack)
6. [Data Model](#6-data-model)
7. [Screens & Features](#7-screens--features)
8. [Authentication Flow](#8-authentication-flow)
9. [MQTT Integration](#9-mqtt-integration)
10. [AI Description Feature](#10-ai-description-feature)
11. [PWA & iOS Requirements](#11-pwa--ios-requirements)
12. [Hosting & Deployment](#12-hosting--deployment)
13. [Development Phases](#13-development-phases)
14. [Risks & Mitigations](#14-risks--mitigations)

**Changelog:**
- v0.2: Added unique box ID creation, Google Sheets import, `Typ`/`Bereich` fields, QR code generation for new entries
- v0.3: Resolved all open questions — QR content is full PWA URL; `bereich` is free text with stepper-motor coordinates; MQTT broker is Adafruit.io with ack/status feedback; Cloudinary photo import; import is standalone one-time prompt; backup is manual on demand
- v0.4: "Send to Machine" button logic defined — routes to `workshop.laser` or `workshop.box` feed on Adafruit.io based on `bereich` format
- v0.5: PWA hosted in `docs/` folder of existing public repo; no build-time secrets; PocketBase URL moved to runtime setup screen
- v1.0: Released. Auth changed from API key to superuser JWT. Actual MQTT topics corrected (`workshop.box`, `workshop.laser`). AI photo description added. Photo crop/rotate editor added. Gallery filter persistence added. PWA icons generated. All phases complete and deployed.

---

## 1. Overview

This document specifies a Progressive Web App (PWA) that replaces an existing Thunkable mobile app + Google Sheets inventory system for a personal workshop.

The system allows the user to:
- Create new inventory entries with an auto-assigned unique box number and generate a printable QR code label
- Scan QR codes attached to workshop boxes and drawers to look up or update entries
- Photograph, crop/rotate, and describe the contents of each box
- Use Claude AI to automatically recognise box contents from a photo and generate a German keyword description
- Classify storage by type (Box, Regal, Boden, Schublade, Sortierbox) and physical coordinates
- Browse the inventory in a thumbnail gallery with persistent search and type filters
- Search and filter inventory items by text, type, and location
- Send a selected box's identifier to an existing MQTT broker for downstream automation (laser pointer, label printer)
- Import the existing inventory from a Google Sheets CSV export (one-time migration)

The PWA is publicly hosted but secured behind a superuser password so that inventory data remains private. It is optimized for Apple iPhones.

**Live URLs:**
- Frontend: `https://jonahpi.github.io/WorkshopEquipment`
- Backend: Fly.io — exact URL configured at runtime in the setup screen

---

## 2. Goals & Non-Goals

### Goals
- Replace Thunkable with a self-maintained, open-source PWA
- Replace Google Sheets with a simple, free, self-hosted database
- Create new inventory entries with auto-assigned unique box numbers and printable QR code labels
- Support QR code scanning and in-app camera use on iOS Safari
- Provide a gallery view with thumbnails and a detail view per item
- Support text search/filtering of the inventory, including by storage type and location, with filter state persisting across navigation
- Allow sending a box identifier to an existing MQTT broker
- Secure access with superuser credentials even though the URL is public
- Work installable as a home-screen app on iPhone
- Import existing inventory from a Google Sheets CSV export (one-time migration action)
- Optionally auto-describe box contents using Claude AI vision

### Non-Goals
- Multi-user accounts or role-based permissions (single-user)
- Real-time collaborative editing
- Barcode scanning (QR only)
- Android optimization (iOS-first; Android may work but is not a target)
- Offline-first / full offline capability (network access assumed)

---

## 3. Users & Access Control

| User type | Description | Access method |
|---|---|---|
| Owner | Single user (workshop owner) | PocketBase superuser email + password |
| Public | Anyone with the URL | None — redirected to setup, no data visible |

On first launch the user enters the PocketBase URL, superuser email and password into the setup screen. The app authenticates with `pb.collection('_superusers').authWithPassword(email, password)` and stores the resulting JWT in `localStorage` as `pb_token`. On subsequent launches the stored JWT is used directly; if it returns 401 the app redirects to the setup screen.

No logout button is provided in normal use — credentials are re-entered via the gear icon on the gallery screen if needed.

---

## 4. System Architecture

```
iPhone (iOS Safari / Home Screen PWA)
│
│  SvelteKit PWA  (GitHub Pages — jonahpi.github.io/WorkshopEquipment)
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  │  Setup   │  │ Gallery  │  │  Detail  │  │ Add Item │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘
│                       │
│             PocketBase JS SDK          mqtt.js (WebSocket)
│
├─── HTTPS ───────────────────────────────────────────────────┐
│                                                              ▼
│                                               Fly.io VM
│                                               ┌─────────────────────┐
│                                               │  PocketBase v0.36.9 │
│                                               │  ├─ pb_data/        │
│                                               │  │  ├─ data.db      │ ← SQLite
│                                               │  │  └─ storage/     │ ← images
│                                               │  └─ pb_hooks/       │
│                                               │     describe.pb.js  │ ← Claude proxy
│                                               └─────────────────────┘
│                                                        │
│                                               Claude API (Anthropic)
│                                               (proxied via PocketBase hook)
│
└─── WSS ─────────────────────────────────────────────────────┐
                                                               ▼
                                               Adafruit.io MQTT Broker
                                               Topics: workshop.box, workshop.laser,
                                                       data (labels)
```

**Add Item data flow:**
```
QR scan (camera) → box_nr
iPhone Camera → photo blob → Cropper.js (crop/rotate) → Canvas resize → FormData
FormData → POST /api/collections/items/records (PocketBase)
                              → SQLite row created
                              → image saved to pb_data/storage/
[optional] base64 image → POST /api/describe (PocketBase hook)
                              → Claude Haiku vision API
                              → German keywords → fills inhalt field
box_nr → mqtt.js → publish to workshop.box or workshop.laser
```

---

## 5. Tech Stack

| Layer | Technology | License | Rationale |
|---|---|---|---|
| Backend / database | [PocketBase v0.36.9](https://pocketbase.io) | MIT | Single binary, SQLite, built-in file/image storage, superuser auth, auto thumbnail generation, JS hooks |
| Frontend framework | [SvelteKit](https://kit.svelte.dev) | MIT | Smallest bundle size, Vite-native, simple reactivity model |
| CSS | [Tailwind CSS](https://tailwindcss.com) | MIT | Mobile-first utilities, tiny purged output |
| PWA tooling | [vite-plugin-pwa](https://vite-pwa-org.netlify.app) (Workbox) | MIT | Service Worker + Web App Manifest generation |
| QR scanning | [html5-qrcode](https://github.com/mebjas/html5-qrcode) | Apache 2.0 | Best iOS Safari support for live-video QR decoding |
| Photo editing | [Cropper.js v1](https://fengyuanchen.github.io/cropperjs/) | MIT | In-browser crop and rotate before upload |
| CSV parsing | [Papa Parse](https://www.papaparse.com) | MIT | Robust in-browser CSV parsing for Google Sheets import |
| MQTT client | [mqtt.js](https://github.com/mqttjs/MQTT.js) | MIT | Browser-compatible, WebSocket transport |
| PocketBase client | [pocketbase JS SDK](https://github.com/pocketbase/js-sdk) | MIT | Official SDK, typed, handles auth headers and file URLs |
| AI description | [Claude Haiku](https://www.anthropic.com) via PocketBase hook | — | Vision API proxied server-side so the API key never reaches the browser |
| PWA hosting | [GitHub Pages](https://pages.github.com) | Free | Served from `docs/` folder of `JonahPi/WorkshopEquipment` repo |
| SvelteKit adapter | [@sveltejs/adapter-static](https://kit.svelte.dev/docs/adapter-static) | MIT | Outputs fully static site to `docs/` |
| Backend hosting | [Fly.io](https://fly.io) | Free tier | Persistent volumes, `min_machines_running=1` prevents cold starts |

---

## 6. Data Model

### Google Sheets → PocketBase field mapping

| Google Sheets column | PocketBase field | Notes |
|---|---|---|
| `BoxNR` | `box_nr` | Preserved as-is; basis for QR code content |
| `Inhalt` | `inhalt` | Contents description (free text or AI-generated keywords) |
| `Typ` | `typ` | Enum — see values below |
| `Bereich` | `bereich` | Location string — see format below |
| `Foto` | `image` | File upload; Cloudinary `http://` URLs rewritten to `https://` at import time |
| `QRcode` | derived | Re-generated from `box_nr` + PWA URL; not stored |

### PocketBase collection: `items`

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | String (auto) | — | PocketBase CUID |
| `box_nr` | Number | Yes | Sequential, unique, immutable after creation |
| `inhalt` | Text | No | Free-text or AI-generated comma-separated keywords in German |
| `typ` | String (enum) | Yes | `Box`, `Regal`, `Boden`, `Schublade`, `Sortierbox` |
| `bereich` | String | No | Free-text location; `x/y` integer format triggers laser routing |
| `image` | File (single) | No | Photo; thumbnails via `?thumb=WxH` |
| `created` | DateTime (auto) | — | |
| `updated` | DateTime (auto) | — | |

### `typ` field — storage system types

| Value | Meaning |
|---|---|
| `Box` | Closed storage box |
| `Regal` | Shelf |
| `Boden` | Floor-level storage |
| `Schublade` | Drawer |
| `Sortierbox` | Numbered sorting/compartment box |

### `bereich` field — location format

| Pattern | Format | Example | Effect |
|---|---|---|---|
| Stepper-motor coordinates | `x/y` — two integers | `3500/2000` | "Send to Machine" routes to `workshop.laser` |
| Descriptive label | Free text, no `int/int` | `Kellertreppe` | "Send to Machine" routes to `workshop.box` |

### `box_nr` — unique ID generation

- On creation, app fetches max `box_nr` from PocketBase and assigns `max + 1`
- Displayed zero-padded where needed (e.g. `042`)
- Immutable after creation (printed on the physical QR code label)

### QR Code content

```
https://jonahpi.github.io/WorkshopEquipment/item/{box_nr}
```

When scanned with the standard iPhone camera, this URL opens the PWA directly at the item's detail view. Existing legacy labels (`http://192.168.10.30/search?b={box_nr}`) continue to work via the in-app QR scanner — the app extracts `box_nr` from the `b` parameter.

### MQTT messages (not persisted)

**Print Label** → `{aio_username}/feeds/data`:
```json
{
  "label_type": "material",
  "data": {
    "box_nr": 42,
    "qr_content": "https://jonahpi.github.io/WorkshopEquipment/item/42",
    "inhalt": "Metrische Schrauben M4-M8, Unterlegscheiben",
    "copies": 1
  }
}
```

**Send to Machine (coordinates)** → `{aio_username}/feeds/workshop.laser`:
```
3500/2000
```

**Send to Machine (box reference)** → `{aio_username}/feeds/workshop.box`:
```
42
```

---

## 7. Screens & Features

### 7.1 Setup Screen

On first launch (or when credentials are missing), a setup screen collects all runtime configuration. Nothing is baked into the build.

**Database (PocketBase):**
- `PocketBase URL` — e.g. `https://your-instance.fly.dev`
- `Admin email` — superuser email
- `Admin password` — superuser password
- "Test connection" button validates credentials; on success stores the resulting JWT as `pb_token` in `localStorage`

**Adafruit.io (MQTT):**
- `AIO Username`
- `AIO Key` (`aio_xxxxxxxxxxxxxxxx`)

**AI Description (optional):**
- `Anthropic API Key` (`sk-ant-xxxxxxxxxxxx`) — if provided, enables the "Describe with AI" button on the Add Item screen

All values pre-populate from `localStorage` on revisit. The gear icon on the gallery header links here.

**Stored `localStorage` keys:** `pb_url`, `pb_token`, `aio_username`, `aio_key`, `anthropic_key`

### 7.2 Gallery View

- 2-column responsive grid of `ItemCard` components
- Each card: thumbnail (200×200, lazy-loaded), `box_nr` badge, `inhalt` preview (2 lines), `typ` chip
- **Search bar** (top): debounced text input filtering `inhalt`, `bereich`, and `box_nr`
- **Filter bar** (collapsible): Typ selector — All | Box | Regal | Boden | Schublade | Sortierbox
- Filter state is persisted in Svelte stores so it survives navigation to detail/edit and back
- **Gear icon** (top-right): links to Setup screen
- Tap a card → Detail View
- Floating action button (bottom-right) → Add Item
- Pull-to-refresh

### 7.3 Detail View

- Full-width image
- Fields: `box_nr` (prominent), `typ` chip, `bereich`, `inhalt` (full text)
- **"Print Label" button**: publishes MQTT message to `{aio_username}/feeds/data`
- **"Send to Machine" button**:
  - `bereich` matches `/^\d+\/\d+$/` → publish `bereich` string to `feeds/workshop.laser`
  - Otherwise → publish `box_nr` string to `feeds/workshop.box`
  - Toast confirmation after publish
- **"Edit" button**: opens item form pre-filled
- **"Delete" button**: confirmation dialog → DELETE from PocketBase → return to Gallery
- Back navigation to Gallery

### 7.4 Add Item Screen

**Step 1 — Assign Box Number**
- Proposes `max box_nr + 1`; user can override
- Duplicate check with inline error
- "Print Label" button available immediately

**Step 2 — Take Photo**
- `<input type="file" accept="image/*" capture="environment">` (iOS camera sheet)
- After selection: **Cropper.js editor** opens full-screen — user can crop and rotate (90° left / right) before confirming
- After confirm: client-side Canvas resize to ≤1920px JPEG 80%
- **"Describe with AI" button** (visible when `anthropic_key` is set and a photo is present): calls the PocketBase `/api/describe` hook, receives comma-separated German keywords, fills the `inhalt` field
- Photo is optional

**Step 3 — Storage Location**
- `typ` selector (segmented control)
- `bereich` free-text input

**Step 4 — Contents**
- `inhalt` multi-line text area (may be pre-filled by AI description)
- "Save" → POST to PocketBase as `multipart/form-data`
- On success: confirmation toast, offer "Add another" or "Go to Gallery"

### 7.5 Edit Item Screen

- Same form as Add Item Steps 3–4
- `box_nr` shown read-only
- Photo replacement with Cropper.js editor
- "Save" → PATCH; "Delete" → DELETE with confirmation

### 7.6 Import Screen

One-time migration from Google Sheets CSV. Shown automatically when the `items` collection is empty; also accessible as a standalone route.

1. Upload CSV (`BoxNR`, `Inhalt`, `Typ`, `Bereich`, `Foto`, `QRcode` columns)
2. Validate: column presence, `Typ` enum values, duplicate `BoxNR`; preview first 5 rows
3. Execute: row-by-row POST with progress bar; `Foto` URLs are rewritten from `http://` to `https://` before fetching, then uploaded to PocketBase; `QRcode` column ignored
4. Report: N imported, M skipped, K photo errors
5. After import: flag stored in `localStorage` to suppress first-run prompt

### 7.7 Navigation

Bottom tab bar (two tabs): Gallery | Add Item  
Settings accessed via gear icon in the gallery header — no dedicated Settings tab.

---

## 8. Authentication Flow

```
App launch
    │
    ▼
Check localStorage for pb_url + pb_token
    │
    ├── Missing → /setup
    │       │
    │       └── User enters URL, email, password
    │               │
    │               ├── Auth fails → show error
    │               └── Auth ok → store pb_token (JWT) → /gallery
    │
    └── Found → PocketBase SDK initialised with stored token
                    │
                    ├── 401 on any API call → clear token → /setup
                    └── OK → render app
```

**Implementation:** `pb.collection('_superusers').authWithPassword(email, password)` → stores `pb.authStore.token` as `pb_token`.

The setup screen pre-populates `pbUrl` and `aioUsername`/`aioKey`/`anthropicKey` from `localStorage` on load, so re-visiting setup doesn't require re-entering all fields. `pbOk` is initialised to `true` if `pb_token` already exists, so the user only needs to click "Save" to continue without re-testing the connection.

---

## 9. MQTT Integration

**Library:** `mqtt.js` with WebSocket (`wss://`) transport  
**Broker:** `wss://io.adafruit.com:443/mqtt`

The MQTT client is a Svelte store initialised after credentials are loaded from `localStorage`. It connects on app mount and auto-reconnects on disconnect.

### Topics

| Direction | Topic | Purpose |
|---|---|---|
| Publish | `{aio_username}/feeds/data` | Print label job |
| Publish | `{aio_username}/feeds/workshop.laser` | Laser pointer coordinates (when `bereich` is `int/int`) |
| Publish | `{aio_username}/feeds/workshop.box` | Box number for generic machine handling |

### Payloads

**Print label** → `feeds/data`:
```json
{
  "label_type": "material",
  "data": {
    "box_nr": 42,
    "qr_content": "https://jonahpi.github.io/WorkshopEquipment/item/42",
    "inhalt": "Metrische Schrauben M4-M8, Unterlegscheiben",
    "copies": 1
  }
}
```

**Laser pointer** → `feeds/workshop.laser` (condition: `bereich` matches `/^\d+\/\d+$/`):
```
3500/2000
```

**Box reference** → `feeds/workshop.box` (condition: `bereich` does not match `int/int`):
```
42
```

Both machine payloads are plain strings — no JSON wrapper.

---

## 10. AI Description Feature

When the user provides an Anthropic API key in the setup screen, a "Describe with AI" button appears on the Add Item screen after a photo is selected.

### Flow

1. User taps "Describe with AI"
2. Frontend extracts the base64-encoded image from the preview canvas (or fetches an existing photo URL)
3. Frontend POSTs to `{pb_url}/api/describe` with `{ image, api_key, media_type }`
4. PocketBase hook (`pb_hooks/describe.pb.js`) proxies the request to the Claude API — the Anthropic key never leaves the server
5. Claude Haiku analyses the image and returns comma-separated German keywords
6. Keywords are inserted into the `inhalt` text field; the user can edit before saving

### PocketBase hook

```js
routerAdd("POST", "/api/describe", (e) => {
  // Validates image + api_key
  // Calls claude-haiku-4-5-20251001 with vision payload
  // Returns { description: "Schrauben, Muttern, Unterlegscheiben" }
});
```

The hook is deployed inside the Docker image at `/pb/pb_hooks/` and loaded via `--hooksDir=/pb/pb_hooks` in the PocketBase serve command.

### Privacy

The Anthropic API key is stored only in the user's `localStorage`. It is sent to the PocketBase backend (over HTTPS) with each describe request and is never logged or stored server-side.

---

## 11. PWA & iOS Requirements

### Web App Manifest

```json
{
  "name": "Workshop Inventory",
  "short_name": "Workshop",
  "display": "standalone",
  "background_color": "#1e3a5f",
  "theme_color": "#1e3a5f",
  "start_url": "/WorkshopEquipment/gallery",
  "icons": [
    { "src": "/WorkshopEquipment/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/WorkshopEquipment/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/WorkshopEquipment/icons/icon-180.png", "sizes": "180x180", "type": "image/png" }
  ]
}
```

Icons: white workshop icon on navy (`#1e3a5f`) background, generated from user-supplied source image via the `sharp` npm library.

### iOS-specific HTML (`app.html`)

```html
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Workshop">
<link rel="apple-touch-icon" href="/WorkshopEquipment/icons/icon-180.png">
```

### Service Worker Caching (Workbox)

| Resource type | Strategy |
|---|---|
| Static assets (JS, CSS, fonts) | Cache First |
| PWA icons / manifest | Cache First |
| API calls (PocketBase) | Network First |
| Image thumbnails | Cache First (LRU 50 items) |

### Camera Access on iOS

- Photo capture: `<input type="file" accept="image/*" capture="environment">` — always works, no permissions API required
- QR scanning: `getUserMedia()` — requires HTTPS, works in iOS 16.4+ as installed PWA; manual `box_nr` entry always available as fallback

---

## 12. Hosting & Deployment

### Backend — Fly.io

- PocketBase v0.36.9 binary in a minimal Alpine-based Docker image
- Persistent Fly.io volume mounted at `/pb_data` (SQLite + image storage)
- Hooks baked into the Docker image at `/pb/pb_hooks/`; loaded via `--hooksDir=/pb/pb_hooks`
- `fly.toml`: `min_machines_running = 1`, internal port 8090, HTTPS via Fly.io auto-TLS
- CORS: `--origins=*` in serve command; GitHub Pages origin additionally allowed in PocketBase Admin UI
- Superuser created via `flyctl ssh console -C "/pb/pocketbase superuser create email password"`

**Dockerfile key points:**
```dockerfile
FROM alpine:3.19
ARG PB_VERSION=0.36.9
COPY backend/pb_migrations /pb/pb_migrations
COPY backend/pb_hooks /pb/pb_hooks
CMD ["/pb/pocketbase", "serve", "--http=0.0.0.0:8090",
     "--dir=/pb_data", "--hooksDir=/pb/pb_hooks", "--origins=*"]
```

### Frontend — GitHub Pages (`docs/` folder)

- **Repository:** `JonahPi/WorkshopEquipment` (public)
- **Served from:** `docs/` on `main` branch
- **Adapter:** `@sveltejs/adapter-static`, `outDir: '../docs'`, `fallback: 'index.html'`
- **Base path:** `base: '/WorkshopEquipment'` in `svelte.config.js`
- **Build:** GitHub Actions workflow on push to `main`:
  1. `cd frontend && npm ci && npm run build` → outputs to `docs/`
  2. Commits and pushes `docs/` back to `main` (with `git pull --rebase` before push to avoid race conditions with concurrent bot commits)
- **No environment variables in the build** — all credentials are runtime, entered by the user

### Backup

Manual on-demand via PocketBase Admin UI → Backups section. Creates a `.zip` of `pb_data/`.

---

## 13. Development Phases

All phases complete.

### Phase 1 — Foundation ✓
- PocketBase deployed to Fly.io; `items` collection created; superuser configured
- SvelteKit + Tailwind CSS + vite-plugin-pwa scaffolded
- Setup screen + JWT auth store
- Gallery view with real data from PocketBase
- GitHub Pages deployment via Actions; base path configured; PocketBase CORS configured

### Phase 2 — Import ✓
- CSV import screen with Papa Parse, column validation, preview, progress bar
- Photo import: `http://` Cloudinary URLs rewritten to `https://`, fetched and uploaded to PocketBase
- First-run prompt dismissed after import via `localStorage` flag

### Phase 3 — Core Features ✓
- Detail view
- Add Item wizard (box_nr auto-assignment, camera, Cropper.js photo editor, form, PocketBase upload)
- Edit Item screen
- Delete item with confirmation
- Search + Typ filter in Gallery (filter state persists across navigation via Svelte stores)
- Tested on physical iPhone

### Phase 4 — MQTT ✓
- `mqtt.js` Svelte store connecting to Adafruit.io via WSS
- "Print Label": publishes to `feeds/data`
- "Send to Machine": routes to `feeds/workshop.laser` (coordinates) or `feeds/workshop.box` (box_nr)
- Validated end-to-end

### Phase 5 — PWA Polish ✓
- Service Worker caching via Workbox
- PWA manifest + iOS meta tags
- Custom icons (white on navy background, generated from user-supplied sample)
- `fallback: 'index.html'` for client-side routing on GitHub Pages

### Phase 6 — AI Description ✓
- PocketBase hook `describe.pb.js` proxying Claude Haiku vision API
- Optional Anthropic API key field in setup screen
- "Describe with AI" button on Add Item screen
- Returns comma-separated German keywords; fills `inhalt` field

---

## 14. Risks & Mitigations

| Risk | Status | Mitigation applied |
|---|---|---|
| QR live-video scan broken on iOS Safari | Monitored | Manual `box_nr` text entry always available as fallback |
| iOS PWA evicts Service Worker cache | Low risk | Auth token in `localStorage` (survives eviction) |
| Images fill Fly.io 1 GB volume | Monitored | Client-side Canvas resize to ≤1920px JPEG 80% before upload |
| MQTT broker lacks WebSocket | Resolved | Using Adafruit.io which supports WSS natively |
| Fly.io cold starts delay first request | Resolved | `min_machines_running = 1` |
| iOS has no native PWA install prompt | Known | User instructed to use Share → Add to Home Screen |
| GitHub Actions bot causes git conflicts | Resolved | `git pull --rebase` before push in deploy workflow |
| Mixed content (HTTP photo URLs on HTTPS page) | Resolved | `http://` rewritten to `https://` at import time |
| PocketBase hooks not loading | Resolved | `--hooksDir=/pb/pb_hooks` added to serve command; hooks baked into Docker image |
