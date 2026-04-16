# Functional Specification Document
# Workshop Inventory PWA

**Version:** 0.2 (Draft for review)
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

> **Open question:** Should there be a way to invalidate/rotate the token without losing access on the phone? (e.g., a "logout" option that clears localStorage)

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
| PWA hosting | [Cloudflare Pages](https://pages.cloudflare.com) | Free tier | Global CDN, HTTPS by default, unlimited static requests |
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

The `bereich` field has two formats depending on `typ`:

| `typ` | `bereich` format | Example |
|---|---|---|
| `Box`, `Regal`, `Boden`, `Schublade` | `x/y` grid coordinates | `3/2` (column 3, row 2) |
| `Sortierbox` | Sorting box number | `7` (compartment or box number 7) |

> **Open question:** For `Sortierbox`, does `bereich` store only the sorting box number (e.g. `7`), or a compartment within a specific box (e.g. `BoxNr/Compartment` like `12/3`)? Clarification needed to finalise the format.

> **Open question:** For `Regal`/`Boden` coordinate system — does x refer to horizontal position and y to vertical (shelf level)? Is there a fixed grid size per storage unit, or are coordinates free-form?

### `box_nr` — unique ID generation

- On creation of a new entry, the app fetches the current maximum `box_nr` from PocketBase and assigns `max + 1`
- `box_nr` is stored as a Number and displayed zero-padded where needed (e.g. `042`)
- `box_nr` is immutable after creation (it is printed on the physical QR code label)
- The QR code content encodes the `box_nr` value as a plain integer string (e.g. `"42"`)

> **Open question:** Should `box_nr` be a plain integer or have a prefix (e.g. `BOX-042`)? This affects what is encoded in the QR code and what is already printed on existing labels.

### QR Code

- Generated client-side from `box_nr` using the `qrcode` npm package (MIT)
- Displayed after new entry creation so the user can screenshot or print the label
- Not stored in the database — always re-generated on demand from `box_nr`

**Thumbnail URL pattern:**
```
https://your-pb.fly.dev/api/files/items/{record_id}/{filename}?thumb=200x200
```
PocketBase generates and caches thumbnails automatically — no additional service required.

### MQTT message (not persisted)

Published to topic `workshop/box/scan` when the user taps "Send to Machine":

```json
{
  "box_nr": 42,
  "timestamp": "2026-04-16T10:30:00Z",
  "action": "scan"
}
```

> **Open question:** Is the MQTT topic `workshop/box/scan` correct? Should the topic include the `box_nr` (e.g. `workshop/box/42`)? What payload format does the downstream consumer expect?

---

## 7. Screens & Features

### 7.1 Login Screen

- Single full-screen form: access token input field + "Unlock" button
- On submit: attempt a lightweight PocketBase API call with the token
  - Success (200) → store token in `localStorage`, navigate to Gallery
  - Failure (401) → show inline error "Invalid token"
- If a valid token already exists in `localStorage`, skip this screen automatically

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
- **"Send to Machine" button**: publishes MQTT message with the item's `box_nr`
  - Shows MQTT connection status (connected / disconnected indicator)
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
- `bereich` input — adapts based on `typ`:
  - If `typ` ≠ Sortierbox: two number inputs labelled "X" and "Y", stored as `"x/y"` string
  - If `typ` = Sortierbox: single number input labelled "Sortierbox Nr."

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

One-time (or occasional) import of existing Google Sheets data.

**Entry point:** Settings menu → "Import from CSV"

**Flow:**

1. **Upload CSV file**
   - `<input type="file" accept=".csv">` — user selects a CSV exported from Google Sheets
   - Expected columns (in any order): `BoxNR`, `Inhalt`, `Typ`, `Bereich`, `Foto`, `QRcode`
   - App parses and previews the first 5 rows in a table for the user to verify

2. **Validate**
   - Check that required columns are present; show error if missing
   - Check each `Typ` value is one of the allowed enum values; flag unknown values
   - Check for duplicate `BoxNR` values within the CSV and against existing PocketBase data
   - Show a summary: "N rows ready to import, M duplicates, K rows with warnings"

3. **Conflict resolution option** (shown if duplicates found):
   - Skip duplicates (default)
   - Overwrite existing records with matching `BoxNR`

4. **Execute import**
   - POST each row to PocketBase sequentially (with a progress bar)
   - `Foto` column: if the value is a URL (Google Drive link), attempt to download and upload the image; if the download fails (auth wall), skip the photo and flag the row — user can add photos manually later
   - `QRcode` column: ignored (re-generated from `BoxNR` on demand)
   - Show final result: "N imported, M skipped, K errors"

> **Open question:** The `Foto` column in Google Sheets likely contains Google Drive URLs that require authentication to access. Should the import silently skip photos (importing text data only) and let the user add photos manually? Or is there a way to pre-export the photos alongside the CSV?

### 7.7 Navigation

iOS-style bottom tab bar with tabs:
- Gallery (home icon)
- Add Item (plus icon)
- Settings (gear icon) — includes Import, logout, app version

> **Open question:** Is a dedicated Settings tab the right home for Import, or should Import be a one-time prompt shown after first login when the database is empty?

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

**Token lifecycle:**
- Stored under key `workshop_token` in `localStorage`
- Attached to all PocketBase SDK requests via `pb.beforeSend` hook
- No expiry enforced at the PWA level (PocketBase API token does not expire unless revoked)
- "Log out" option (if implemented) clears `localStorage` and redirects to `/login`

---

## 9. MQTT Integration

**Library:** `mqtt.js` with WebSocket (`wss://`) transport

**Connection:**
- MQTT client initialized as a Svelte store on app startup (after authentication)
- Broker URL and credentials stored as environment variables (`PUBLIC_MQTT_BROKER_URL`, `PUBLIC_MQTT_TOPIC`)
- Auto-reconnect on disconnect (mqtt.js built-in)
- Connection state (`connected` / `disconnected`) exposed in the store and shown in Detail View UI

**Publish — two topics:**

| Action | Topic | Triggered from | Payload |
|---|---|---|---|
| Send to machine | `workshop/box/scan` | Detail View "Send to Machine" button | See Section 6 |
| Print QR label | `workshop/box/print` | Detail View "Print Label" button, Add Item Step 1 | `{ "box_nr": 42 }` |

Both are QoS 0 (fire-and-forget). The label-printing app subscribes to `workshop/box/print` and handles QR code generation and physical printing independently.

> **Open question:** What is the correct MQTT topic for label printing (e.g. `workshop/box/print`)? What payload format does the label-printing app expect?

**Broker requirements:**
- Must support WebSocket transport (port 9001 or 443/wss)
- If the existing broker is Mosquitto, add to `mosquitto.conf`:
  ```
  listener 9001
  protocol websockets
  ```

> **Open question:** Does the existing MQTT broker support WebSocket connections? If not, which option is preferred: (a) configure WebSocket on existing broker, (b) add a lightweight relay, or (c) use a public test broker like HiveMQ for now?

> **Open question:** Is MQTT authentication (username/password) required for the broker?

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
- CORS configured in PocketBase Admin UI to allow requests from the Cloudflare Pages domain

### Frontend — Cloudflare Pages

- Connected to the GitHub repository
- Build command: `cd frontend && npm run build`
- Output directory: `frontend/.svelte-kit/cloudflare`
- Environment variables set in Cloudflare Pages dashboard:
  - `PUBLIC_PB_URL` — PocketBase instance URL
  - `PUBLIC_MQTT_BROKER_URL` — MQTT broker WebSocket URL
  - `PUBLIC_MQTT_TOPIC` — MQTT topic

### Backup Strategy

- PocketBase built-in backup API: `POST /api/backups` → creates a `.zip` of `pb_data/`
- Schedule: nightly backup via PocketBase's cron hook or external cron trigger
- Destination: TBD (local download, Fly.io volume snapshot, or Backblaze B2)

> **Open question:** Where should backups be stored? Options: (a) manual download on demand, (b) automated to Backblaze B2 (free tier 10 GB), (c) Fly.io volume snapshots.

---

## 12. Development Phases

### Phase 1 — Foundation
- [ ] Deploy PocketBase to Fly.io; create `items` collection (with `box_nr`, `inhalt`, `typ`, `bereich`, `image` fields); generate API token
- [ ] Scaffold SvelteKit + Tailwind CSS + vite-plugin-pwa
- [ ] Login screen + token store (`localStorage`)
- [ ] Gallery view with real data from PocketBase (including Typ chips and Bereich display)
- [ ] Deploy frontend to Cloudflare Pages; configure CORS

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
- [ ] mqtt.js store: connect, reconnect, publish
- [ ] "Send to Machine" button on Detail view
- [ ] Connection status indicator
- [ ] Validate with existing broker

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

Items requiring decisions before or during implementation:

### Data model
1. **`box_nr` format:** Should `box_nr` be stored and encoded in QR codes as a plain integer (e.g. `42`) or with a prefix (e.g. `BOX-042`)? This must match what is already printed on existing physical labels.
2. **`bereich` for Sortierbox:** Does `bereich` store only the sorting box number (e.g. `7`), or a compartment within a specific box (e.g. `12/3`)? Is there ever a case where a Sortierbox item also has x/y coordinates?
3. **`bereich` coordinate system:** For `Regal`/`Boden` — does x = horizontal position and y = vertical (shelf level)? Is there a maximum grid size, or are coordinates free-form integers?

### Import
4. **Photos in Google Sheets:** The `Foto` column likely contains Google Drive URLs requiring authentication. Should the import skip photos entirely (text-only import, photos added manually later), or is there a way to pre-export images alongside the CSV?
5. **Import trigger:** Should the Import function live in a Settings tab (always accessible) or be shown as a one-time prompt when the database is empty after first login?
6. **Duplicate handling default:** When the same `BoxNR` exists in both the CSV and PocketBase, should the default be "skip" (preserve existing) or "overwrite" (take CSV version)?

### MQTT
7. **MQTT scan topic format:** Should the topic be `workshop/box/scan` (flat) or `workshop/box/{box_nr}` (per-box topics)?
8. **MQTT scan payload format:** What does the downstream machine consumer expect? (JSON vs plain integer string vs custom format)
9. **MQTT label-printing topic:** What is the correct topic name for the label-printing app? What payload format does it expect?
10. **MQTT broker WebSocket:** Does the existing broker support WSS? Username/password required?

### UX / Access
10. **Token rotation:** Is a "Log Out" / "Change Token" feature needed in the UI?
11. **Backup destination:** Where should automated PocketBase backups go? Options: (a) manual download on demand, (b) Backblaze B2 free tier (10 GB), (c) Fly.io volume snapshots.
12. **Offline priority:** How important is offline Add Item support? (affects Phase 5 complexity significantly)
