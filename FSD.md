# Functional Specification Document
# Workshop Inventory PWA

**Version:** 0.5 (Draft for review)
**Author:** TBD
**Date:** 2026-04-16
**Status:** Draft — pending review and refinement

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
10. [PWA & iOS Requirements](#10-pwa--ios-requirements)
11. [Hosting & Deployment](#11-hosting--deployment)
12. [Development Phases](#12-development-phases)
13. [Risks & Mitigations](#13-risks--mitigations)
14. [Open Questions](#14-open-questions)

**Changelog:**
- v0.2: Added unique box ID creation, Google Sheets import, `Typ`/`Bereich` fields, QR code generation for new entries
- v0.3: Resolved all open questions — QR content is full PWA URL; `bereich` is free text with stepper-motor coordinates; MQTT broker is Adafruit.io with ack/status feedback; Cloudinary photo import; import is standalone one-time prompt; backup is manual on demand
- v0.4: "Send to Machine" button logic defined — routes to `stepper.position` or `box` feed on Adafruit.io based on `bereich` format; all open questions resolved
- v0.5: PWA hosted in `docs/` folder of existing public repo; no build-time secrets; PocketBase URL moved to runtime setup screen

---

## 1. Overview

This document specifies a Progressive Web App (PWA) that replaces an existing Thunkable mobile app + Google Sheets inventory system for a personal workshop.

The system allows the user to:
- Create new inventory entries with an auto-assigned unique box number and generate a printable QR code label
- Scan QR codes attached to workshop boxes and drawers to look up or update entries
- Photograph and describe the contents of each box
- Classify storage by type (Box, Regal, Boden, Schublade, Sortierbox) and physical coordinates
- Browse the inventory in a thumbnail gallery
- Search and filter inventory items by text, type, and location
- Send a selected box's identifier to an existing MQTT broker for downstream automation
- Import the existing inventory from a Google Sheets CSV export (one-time migration)

The PWA is publicly hosted but secured behind an access token so that inventory data remains private. It is optimized for Apple iPhones.

---

## 2. Goals & Non-Goals

### Goals
- Replace Thunkable with a self-maintained, open-source PWA
- Replace Google Sheets with a simple, free, self-hosted database
- Create new inventory entries with auto-assigned unique box numbers and printable QR code labels
- Support QR code scanning and in-app camera use on iOS Safari
- Provide a gallery view with thumbnails and a detail view per item
- Support text search/filtering of the inventory, including by storage type and location
- Allow sending a box identifier to an existing MQTT broker
- Secure access with a token even though the URL is public
- Work installable as a home-screen app on iPhone
- Import existing inventory from a Google Sheets CSV export (one-time migration action)

### Non-Goals
- Multi-user accounts or role-based permissions (single-user or single shared token)
- Real-time collaborative editing
- Barcode scanning (QR only)
- Android optimization (iOS-first; Android may work but is not a target)
- Offline-first / full offline capability (network access assumed; basic offline queue is a nice-to-have)

---

## 3. Users & Access Control

| User type | Description | Access method |
|---|---|---|
| Owner | Single user (workshop owner) | Static shared access token |
| Public | Anyone with the URL | None — redirected to login, no data visible |

The access token is a single static string stored in PocketBase's admin settings (API key). The user enters it once in the PWA login screen; it is stored in `localStorage` and reused on subsequent visits.

Token invalidation is handled via the PocketBase Admin UI — revoking the token there causes the next API call from the phone to return `401`, which the app already handles by redirecting to the setup screen. No logout button needed in the PWA.

---

## 4. System Architecture

```
iPhone (iOS Safari / Home Screen PWA)
│
│  SvelteKit PWA
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  │  Login   │  │ Gallery  │  │  Detail  │  │ Add Item │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘
│                       │
│             PocketBase JS SDK          mqtt.js (WebSocket)
│
├─── HTTPS ───────────────────────────────────────────────────┐
│                                                              ▼
│                                               Fly.io VM
│                                               ┌─────────────────┐
│                                               │  PocketBase     │
│                                               │  ├─ data.db     │  ← SQLite
│                                               │  └─ storage/    │  ← images
│                                               └─────────────────┘
│
└─── WSS ─────────────────────────────────────────────────────┐
                                                               ▼
                                               Existing MQTT Broker
                                               Topic: workshop/box/scan
```

**Add Item data flow:**
```
QR scan (camera) → box_id
iPhone Camera → photo blob → resize (Canvas API) → FormData
FormData → POST /api/collections/items/records (PocketBase)
                              → SQLite row created
                              → image saved to pb_data/storage/
box_id → mqtt.js → publish to workshop/box/scan
```

---

## 5. Tech Stack

| Layer | Technology | License | Rationale |
|---|---|---|---|
| Backend / database | [PocketBase](https://pocketbase.io) | MIT | Single binary, SQLite, built-in file/image storage, API token auth, auto thumbnail generation |
| Frontend framework | [SvelteKit](https://kit.svelte.dev) | MIT | Smallest bundle size, Vite-native, simple reactivity model |
| CSS | [Tailwind CSS](https://tailwindcss.com) | MIT | Mobile-first utilities, tiny purged output |
| PWA tooling | [vite-plugin-pwa](https://vite-pwa-org.netlify.app) (Workbox) | MIT | Service Worker + Web App Manifest generation |
| QR scanning | [html5-qrcode](https://github.com/mebjas/html5-qrcode) | Apache 2.0 | Best iOS Safari support for live-video QR decoding |
| CSV parsing | [Papa Parse](https://www.papaparse.com) | MIT | Robust in-browser CSV parsing for Google Sheets import |
| MQTT client | [mqtt.js](https://github.com/mqttjs/MQTT.js) | MIT | Browser-compatible, WebSocket transport |
| PocketBase client | [pocketbase JS SDK](https://github.com/pocketbase/js-sdk) | MIT | Official SDK, typed, handles auth headers and file URLs |
| PWA hosting | [GitHub Pages](https://pages.github.com) | Free | Served from `docs/` folder of existing public repo `JonahPi/WorkshopEquipment`; no separate repo needed |
| SvelteKit adapter | [@sveltejs/adapter-static](https://kit.svelte.dev/docs/adapter-static) | MIT | Outputs a fully static site; build output directed to `docs/` |
| Backend hosting | [Fly.io](https://fly.io) | Free tier | Persistent volumes, no auto-sleep with `min_machines_running=1` |

---

## 6. Data Model

### Google Sheets → PocketBase field mapping

The existing Google Sheets export has these columns:

| Google Sheets column | PocketBase field | Notes |
|---|---|---|
| `BoxNR` | `box_nr` | Preserved as-is; becomes the basis for QR code content |
| `Inhalt` | `inhalt` | Contents description (free text) |
| `Typ` | `typ` | Enum — see values below |
| `Bereich` | `bereich` | Location string — see format below |
| `Foto` | `image` | File upload (see import note on photos) |
| `QRcode` | derived | Re-generated from `box_nr`; not stored separately |

### PocketBase collection: `items`

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | String (auto) | — | PocketBase CUID, internal use only |
| `box_nr` | Number | Yes | Human-readable sequential box number, e.g. `42`. Unique. Auto-assigned on creation (max existing + 1). |
| `inhalt` | Text | No | Free-text description of box contents |
| `typ` | String (enum) | Yes | One of: `Box`, `Regal`, `Boden`, `Schublade`, `Sortierbox` |
| `bereich` | String | No | Location identifier — see format below |
| `image` | File (single) | No | Photo of box contents; thumbnails auto-generated via `?thumb=WxH` |
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

`bereich` is a free-text string. Two patterns appear in practice:

| Pattern | Format | Example | Used when |
|---|---|---|---|
| Stepper-motor coordinates | `x/y` — two integers 0–10000 | `3500/2000` | Storage has a precise physical location the laser pointer can target |
| Descriptive label | Free text, no numbers | `Kellertreppe`, `Regal`, `Schrank` | General area without precise coordinates |

The "Send to Machine" action passes `bereich` directly to the downstream machine, which uses x/y values to drive stepper motors and point a laser at the correct storage location. Descriptive values are passed as-is and ignored by the motor controller.

The UI input is a **single free-text field** — no structured x/y split.

### `box_nr` — unique ID generation

- On creation of a new entry, the app fetches the current maximum `box_nr` from PocketBase and assigns `max + 1`
- `box_nr` is stored as a Number and displayed zero-padded where needed (e.g. `042`)
- `box_nr` is immutable after creation (it is printed on the physical QR code label)

### QR Code content

The QR code encodes the **full PWA URL** for the item, not just the box number:

```
https://jonahpi.github.io/WorkshopEquipment/item/{box_nr}
```

When scanned with the standard iPhone camera (no app needed), this URL opens the PWA directly at the item's detail view. If the PWA is not installed, iOS Safari opens it as a web page.

Existing physical labels encode `http://192.168.10.30/search?b={box_nr}` — these continue to work via the QR scanner inside the app (the app extracts `box_nr` from the URL parameter `b`).

The QR code is not stored in the database; the content is always derived from `box_nr` and the known PWA base URL at print time.

**Thumbnail URL pattern:**
```
https://your-pb.fly.dev/api/files/items/{record_id}/{filename}?thumb=200x200
```
PocketBase generates and caches thumbnails automatically — no additional service required.

### MQTT messages (not persisted)

**Send to Machine** — topic depends on `bereich` format (see Section 9):

- If `bereich` matches `integer/integer` → topic `ToniTwn/feeds/stepper.position`, value: the `bereich` string (e.g. `"3500/2000"`)
- Otherwise → topic `ToniTwn/feeds/box`, value: the `box_nr` integer (e.g. `42`)

**Print Label** — topic `ToniTwn/feeds/data` on Adafruit.io (see Section 9):
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

---

## 7. Screens & Features

### 7.1 Login / Setup Screen

On first launch (or when credentials are missing from `localStorage`), a setup screen collects all runtime configuration. Nothing is baked into the build — the same static files work regardless of backend location.

**PocketBase connection** (gates inventory data):
- `PocketBase URL` — e.g. `https://your-instance.fly.dev`
- `Access token` — the API key from PocketBase admin settings
- "Verify" button: tests the URL + token with a lightweight API call
  - 200 → proceed; error → show inline message

**Adafruit.io credentials** (required for MQTT / label printing and machine control):
- `AIO Username` — e.g. `ToniTwn`
- `AIO Key` — `aio_xxxxxxxxxxxxxxxx`
- Optional "Test connection" button

All four values are stored in `localStorage` (`pb_url`, `pb_token`, `aio_username`, `aio_key`). On subsequent launches, if all are present, this screen is skipped entirely.

**No credentials appear anywhere in the repository or build output.**

### 7.2 Gallery View

- 2-column responsive grid of `ItemCard` components
- Each card shows:
  - Thumbnail image (200×200, lazy-loaded)
  - `box_nr` badge (top-left overlay, zero-padded)
  - `inhalt` preview (truncated to 2 lines)
  - `typ` chip (colour-coded by type)
- **Search bar** at the top:
  - Debounced text input — filters on `inhalt` and `bereich`
  - For ≤ 500 items: client-side filter on loaded data
  - For larger datasets: PocketBase server-side filter via `?filter=inhalt~"query"||bereich~"query"`
- **Filter bar** (collapsible, below search):
  - Typ selector: All | Box | Regal | Boden | Schublade | Sortierbox
  - Combined with search text using AND logic
- Tap a card → navigate to Detail View
- Floating action button (bottom-right) → navigate to Add Item
- Pull-to-refresh to reload data

### 7.3 Detail View

- Full-width image (tap to zoom / pinch-zoom)
- Fields displayed:
  - `box_nr` (prominent, large)
  - `typ` chip
  - `bereich` (formatted as `x/y` or `Sortierbox N`)
  - `inhalt` (full text)
- **"Print Label" button**: publishes an MQTT message to the label-printing topic with the item's `box_nr` — a separate app handles actual QR code generation and printing
- **"Send to Machine" button**: routing logic based on `bereich` value:
  - If `bereich` matches the pattern `integer/integer` (e.g. `3500/2000`) → publishes the `bereich` string to `ToniTwn/feeds/stepper.position` (drives the laser pointer to the storage location)
  - Otherwise → publishes `box_nr` to `ToniTwn/feeds/box` (sends the box number for generic machine handling)
  - Shows printer/machine connection status indicator
  - Confirms send with a toast notification
- **"Edit" button**: opens the item form pre-filled for editing
- Back navigation to Gallery

### 7.4 Add Item Screen

Four-step wizard for creating a new inventory entry:

**Step 1 — Assign Box Number**
- System fetches the current maximum `box_nr` from PocketBase and proposes `max + 1`
- User can accept the proposed number or enter a custom one (for filling gaps)
- Duplicate check: if `box_nr` already exists, show an inline error
- **"Print Label" button**: publishes an MQTT message to the label-printing topic with the new `box_nr` — the external label-printing app receives this and prints the QR code label to attach to the physical box
- User can trigger printing before or after filling in the remaining steps

**Step 2 — Take Photo**
- `<input type="file" accept="image/*" capture="environment">` (triggers native iOS camera sheet)
- After selection: preview thumbnail shown
- Client-side image resize: scale to max 1920px on longest side, JPEG quality 80% (via Canvas API), target ~200–500 KB per image
- "Retake" option available
- Photo is optional — can skip

**Step 3 — Storage Location**
- `typ` selector: segmented control (Box / Regal / Boden / Schublade / Sortierbox)
- `bereich` input: single free-text field — user enters either stepper-motor coordinates (`3500/2000`) or a descriptive label (`Kellertreppe`); no validation enforced

**Step 4 — Contents**
- `inhalt`: multi-line text area
- "Save" button → POST to PocketBase with image as `multipart/form-data`
- On success → show confirmation toast; offer "Add another" or "Go to Gallery"
- On failure → show error toast; queue locally if offline

### 7.5 Edit Item Screen

- Same form layout as Add Item Steps 3–4 (no Step 1/2 re-entry)
- `box_nr` is shown read-only (cannot be changed after creation)
- Photo can be replaced (shows current photo, offers "Change Photo")
- "Save" → PATCH to PocketBase
- "Delete" button (with confirmation dialog) → DELETE from PocketBase → return to Gallery

### 7.6 Import Screen

One-time import of existing Google Sheets data. Shown automatically as a prompt when the PocketBase `items` collection is empty after first login. Can also be a standalone script run outside the PWA if preferred.

**Flow:**

1. **Upload CSV file**
   - `<input type="file" accept=".csv">` — user selects a CSV exported from Google Sheets
   - Expected columns (in any order): `BoxNR`, `Inhalt`, `Typ`, `Bereich`, `Foto`, `QRcode`
   - App parses (Papa Parse) and previews the first 5 rows for verification

2. **Validate**
   - Check required columns are present; show error if missing
   - Check each `Typ` value is a known enum value; flag unknowns as warnings
   - Check for duplicate `BoxNR` values; duplicates are skipped (existing record preserved)
   - Show summary: "N rows ready to import, M duplicates skipped, K warnings"

3. **Execute import**
   - POST each row to PocketBase sequentially with a progress bar
   - `Foto` column: contains public Cloudinary URLs (e.g. `https://res.cloudinary.com/dh04w3wmx/image/upload/...`) — fetch each image directly and upload to PocketBase as a file attachment; log any fetch failures and continue
   - `QRcode` column: ignored (QR content is derived from `box_nr` + PWA URL at print time)
   - Show final result: "N imported, M skipped, K photo errors"

4. **After import**: prompt is dismissed and not shown again (flag stored in `localStorage`)

### 7.7 Navigation

iOS-style bottom tab bar with two tabs:
- Gallery (home icon)
- Add Item (plus icon)

No Settings tab — credentials are entered once at setup and no logout or settings changes are needed during normal use.

---

## 8. Authentication Flow

```
App launch
    │
    ▼
Check localStorage for token
    │
    ├── No token → /login
    │       │
    │       └── User submits token
    │               │
    │               ├── 401 → show error
    │               └── 200 → save to localStorage → /gallery
    │
    └── Token found → validate (lightweight API call)
                │
                ├── 401 → clear localStorage → /login
                └── 200 → render app
```

**Credential lifecycle:**
- `pb_url` and `pb_token` stored in `localStorage`; PocketBase SDK initialised with the runtime URL on app start
- Token attached to all PocketBase SDK requests via `pb.beforeSend` hook
- No expiry enforced at the PWA level (PocketBase API token does not expire unless revoked)
- Nothing is hardcoded in the build — the same `docs/` output works against any PocketBase instance

---

## 9. MQTT Integration

**Library:** `mqtt.js` with WebSocket (`wss://`) transport

### Broker — Adafruit.io

The label-printing MQTT broker is hosted on **Adafruit.io** (`io.adafruit.com`), which supports WebSocket natively over `wss://io.adafruit.com:443/mqtt`.

**Credentials** (user-entered once at setup, stored in `localStorage`):

| Key | Description |
|---|---|
| `aio_username` | Adafruit.io username (e.g. `ToniTwn`) |
| `aio_key` | Adafruit.io API key (`aio_xxxxxxxxxxxxxxxx`) |

Entered on the setup screen, persisted in `localStorage`. Not present anywhere in the repository or build output.

### MQTT Topics

| Direction | Topic | Purpose |
|---|---|---|
| Publish | `{aio_username}/feeds/data` | Send label-print job to printer |
| Publish | `{aio_username}/feeds/stepper.position` | Drive laser pointer to storage location (when `bereich` is `int/int`) |
| Publish | `{aio_username}/feeds/box` | Send box number to machine (when `bereich` is descriptive text) |
| Subscribe | `{aio_username}/feeds/ack` | Printer confirmed receipt: `{"received": true}` |
| Subscribe | `{aio_username}/feeds/status` | Printer status: `{"printer": "offline"}` if unavailable |

### Connection behaviour

- MQTT client is a Svelte store, initialized after credentials are loaded from `localStorage`
- Subscribes to `feeds/ack` and `feeds/status` immediately on connect
- Auto-reconnect on disconnect (mqtt.js built-in)
- Printer status (`online` / `offline`) displayed in the Detail View near the "Print Label" button
- On "Print Label" tap: publish, then wait up to 5 s for `feeds/ack` response; show toast "Label sent ✓" or "No confirmation received"

### Payloads

**Print label** → `{aio_username}/feeds/data` (QoS 0):
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

**Send to machine — stepper position** → `{aio_username}/feeds/stepper.position` (QoS 0):

Condition: `bereich` matches regex `/^\d+\/\d+$/`

```
3500/2000
```
Plain string value — the downstream stepper-motor controller parses x and y from the `integer/integer` format and positions the laser pointer accordingly.

**Send to machine — box reference** → `{aio_username}/feeds/box` (QoS 0):

Condition: `bereich` does **not** match `integer/integer` (e.g. `Kellertreppe`, `Schrank`)

```
42
```
Plain integer value — the `box_nr`, for generic machine handling when no precise coordinates are available.

---

## 10. PWA & iOS Requirements

### Web App Manifest (`manifest.webmanifest`)

```json
{
  "name": "Workshop Inventory",
  "short_name": "Workshop",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#1a1a2e",
  "start_url": "/gallery",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icons/icon-180.png", "sizes": "180x180", "type": "image/png" }
  ]
}
```

### iOS-specific HTML (in `app.html`)

```html
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Workshop">
<link rel="apple-touch-icon" href="/icons/icon-180.png">
```

### "Add to Home Screen" Prompt

iOS Safari does not fire a native PWA install prompt. Implement a custom banner:
- Shown on first visit (or when `window.navigator.standalone !== true`)
- Text: "Install this app: tap the Share button, then 'Add to Home Screen'"
- Include a visual indicator pointing to the Share button
- Dismiss button (remembers dismissal in `localStorage`)

### Service Worker Caching Strategy (Workbox)

| Resource type | Strategy | Notes |
|---|---|---|
| Static assets (JS, CSS, fonts) | Cache First | Long cache TTL; versioned by Vite hash |
| PWA icons / manifest | Cache First | |
| API calls (PocketBase) | Network First | Falls back to cached response if offline |
| Image thumbnails | Cache First | Cached with a 50-item LRU limit to manage storage |

### Camera Access on iOS

- Photo capture: `<input type="file" accept="image/*" capture="environment">` — always works on iOS, triggers native camera UI, no permissions API required
- QR scanning: `getUserMedia()` with video constraints — requires HTTPS, works in iOS 16.4+ when installed as PWA. Always provide manual text fallback.

---

## 11. Hosting & Deployment

### Backend — Fly.io

- PocketBase binary wrapped in a minimal Dockerfile
- Fly.io persistent volume (1 GB free) mounted at `/pb_data` for SQLite + images
- `fly.toml` configuration:
  - `min_machines_running = 1` (prevents cold starts)
  - Internal port: 8090 (PocketBase default)
  - HTTPS via Fly.io auto-TLS
- CORS configured in PocketBase Admin UI to allow requests from `https://jonahpi.github.io`

### Frontend — GitHub Pages (`docs/` folder)

- **Repository:** `JonahPi/WorkshopEquipment` (existing public repo — no separate repo needed)
- **Served from:** `docs/` folder on the `main` branch (configured in repo Settings → Pages → Source)
- **Adapter:** `@sveltejs/adapter-static` with `outDir: '../docs'` in `svelte.config.js`
- **Build:** GitHub Actions workflow triggered on push to `main`:
  1. `cd frontend && npm ci && npm run build` — outputs static files to `docs/`
  2. Commits and pushes the updated `docs/` folder back to `main`
- **No environment variables in the build** — all backend URLs and credentials are entered by the user at runtime and stored in `localStorage`. The build is completely credential-free.
- **HTTPS:** Provided automatically by GitHub Pages
- **CORS:** PocketBase must allow requests from `https://jonahpi.github.io`
- **SvelteKit base path:** Set `base: '/WorkshopEquipment'` in `svelte.config.js` so all asset and route paths resolve correctly under the repo sub-path
- **Client-side routing fallback:** Copy `docs/index.html` to `docs/404.html` in the build step so that deep-linked URLs (e.g. `/WorkshopEquipment/item/42`) are served correctly by GitHub Pages

### Backup Strategy

- PocketBase built-in backup API: `POST /api/backups` → creates a `.zip` of `pb_data/`
- Schedule: nightly backup via PocketBase's cron hook or external cron trigger
- Destination: manual on-demand download via PocketBase Admin UI (`/api/backups`)

---

## 12. Development Phases

### Phase 1 — Foundation
- [ ] Deploy PocketBase to Fly.io; create `items` collection (with `box_nr`, `inhalt`, `typ`, `bereich`, `image` fields); generate API token
- [ ] Scaffold SvelteKit + Tailwind CSS + vite-plugin-pwa
- [ ] Login screen + token store (`localStorage`)
- [ ] Gallery view with real data from PocketBase (including Typ chips and Bereich display)
- [ ] Configure GitHub Pages to serve from `docs/` on `main`; set SvelteKit `base: '/WorkshopEquipment'` and `outDir: '../docs'`; add GitHub Actions build workflow; configure PocketBase CORS for `jonahpi.github.io`

**Milestone:** Can log in and see inventory items in a gallery.

### Phase 2 — Import
- [ ] CSV import screen: file upload, Papa Parse, column validation, preview
- [ ] Import execution: row-by-row POST to PocketBase, progress indicator, conflict handling
- [ ] Photo import: attempt Google Drive URL download; skip and flag on failure
- [ ] Run full import of existing Google Sheets data; verify in gallery

**Milestone:** Existing inventory is in PocketBase and visible in the PWA.

### Phase 3 — Core Features
- [ ] Detail view (with QR code display button)
- [ ] Add Item wizard: Step 1 (box_nr assignment + QR preview) + Step 2 (camera + resize) + Step 3 (Typ/Bereich form) + Step 4 (Inhalt + submit)
- [ ] Edit Item screen
- [ ] Delete item (with confirmation)
- [ ] Search + Typ filter in Gallery
- [ ] **Test on physical iPhone** (not browser emulator)

**Milestone:** Full inventory management works end-to-end on iPhone.

### Phase 4 — MQTT
- [ ] mqtt.js store: connect to Adafruit.io via WSS with AIO credentials from `localStorage`; auto-reconnect
- [ ] Subscribe to `feeds/ack` and `feeds/status`; expose printer status in store
- [ ] "Print Label" button: publish to `{aio_username}/feeds/data`; await ack toast
- [ ] "Send to Machine" button: evaluate `bereich` format → publish to `feeds/stepper.position` (coordinates) or `feeds/box` (box_nr)
- [ ] Printer online/offline indicator in Detail View
- [ ] Validate end-to-end with physical printer

**Milestone:** Box scan triggers MQTT message.

### Phase 5 — PWA Polish
- [ ] Service Worker caching (Workbox strategies)
- [ ] Offline queue for failed Add Item submissions
- [ ] PWA manifest + iOS meta tags + icons
- [ ] "Add to Home Screen" instruction banner
- [ ] Test Add-to-Home-Screen on iPhone

**Milestone:** Installable, feels native on iPhone.

### Phase 6 — Hardening
- [ ] Automated PocketBase backup
- [ ] Error boundaries + offline indicator
- [ ] README with full setup instructions

---

## 13. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| QR live-video scan broken on iOS Safari | Medium | Medium | Always provide manual `box_id` text entry as fallback |
| iOS PWA evicts Service Worker cache | Low | Low | Auth token in `localStorage` (survives eviction); offline queue is manual |
| Images fill Fly.io 1 GB volume | Medium | Medium | Resize client-side to ≤1920px JPEG 80% before upload (~300 KB/image) |
| MQTT broker lacks WebSocket support | Medium | High | Enable WebSocket on existing broker (2-line Mosquitto config) or deploy relay |
| Fly.io cold starts delay first request | Low | Low | `min_machines_running = 1` prevents machine sleep |
| iOS has no native PWA install prompt | High (certain) | Low | Custom "Add to Home Screen" banner with instructions |

---

## 14. Open Questions

All questions resolved. No open items.

12. **Offline priority:** How important is offline Add Item support? (affects Phase 5 complexity significantly)

    answer: not important
