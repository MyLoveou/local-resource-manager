## Purpose

Project-wide performance and hygiene: SQLite, import workers, HTTP, 10k-scale grid, viewer, explicit library reset. API remains the source of truth for any future remote backend.

## ADDED Requirements

### Requirement: Measure before claiming wins

Work SHALL be sequenced S0 then S1–S6. Later stages without S0 evidence are not complete.

#### Scenario: Baseline exists

- **WHEN** implementers start S1
- **THEN** tests.md records measurements or an explicit “no corpus, qualitative only” note
- **对应测试**：`tests.md` G0

### Requirement: Library writes stay on the backend

Renderer SHALL NOT copy, hash, thumbnail, or open SQLite. All mutations and library file reads go through HTTP so a future hosted backend can reuse the same contract. Frontend MAY cache, virtualize, and keep UI drafts.

#### Scenario: Import a file

- **WHEN** the user confirms import
- **THEN** the renderer only sends paths (or later upload) to the API; bytes are copied by the backend
- **对应测试**：`tests.md` G-ARCH

### Requirement: List and detail queries stay cheap

List pages SHALL use indexes matching `(status, type, created_at, id)` and a slim DTO. Deep pages SHALL use keyset pagination (offset MAY remain compatible). Detail SHALL load relations without sequential per-table gets.

#### Scenario: List page

- **WHEN** `GET /library/resources?type=image&status=active`
- **THEN** SQL can use the composite index; the payload omits files/todos
- **对应测试**：`tests.md` G1

### Requirement: Bulk import does not freeze the app

Hash, copy, probe, and thumbnail SHALL run off the asyncio event loop. CPU workers MAY run in parallel up to `min(4, CPU-1)`. SQLite writes SHALL be serialized on one writer. Import SHALL be a background job with progress polling so HTTP list requests still succeed during ingest.

#### Scenario: Import many files

- **WHEN** the user imports hundreds or thousands of files
- **THEN** the window stays responsive, progress updates, and `GET /library/resources` returns 200
- **对应测试**：`tests.md` G2

### Requirement: Thumbnails everywhere except the image viewer

All `<img>` surfaces except the inline image viewer SHALL use `thumbnailPath` only. They SHALL NOT fall back to `coverPath` or `/content`. Missing thumbnails SHALL show a placeholder. The viewer is the only client that may request `/content`. Video grid and panels follow the same thumbnail rule.

#### Scenario: Browse without opening viewer

- **WHEN** the user scrolls the image grid and opens the info panel or edit modal
- **THEN** network activity has thumbnail URLs only; no `/content` until the viewer opens
- **对应测试**：`tests.md` G3c

### Requirement: Ten-thousand-item grid stays interactive

The grid SHALL render only the viewport plus overscan. Cards SHALL NOT use `/content` or `coverPath` as the cover. `library.bump` SHALL NOT reload every loaded page from offset 0 in a way that freezes the UI.

#### Scenario: Scroll a 10k library

- **WHEN** about 10000 active resources exist
- **THEN** scrolling and clicking a card remain usable; DOM node count stays near the viewport
- **对应测试**：`tests.md` G3b

### Requirement: Static media is cacheable; vocab does not block first paint

Thumbnail and content responses SHALL send Cache-Control. Grid first paint SHALL NOT await category/tag lists. Panel preview SHALL use the thumbnail or a placeholder, never original content.

#### Scenario: Open image page then select

- **WHEN** the user opens Images then clicks a card
- **THEN** the grid appears without waiting for vocab; panel preview is thumbnail or placeholder, never `/content`
- **对应测试**：`tests.md` G3

### Requirement: Viewer gestures remain in the wrapper

Viewer open SHALL be the first `/content` fetch for that id. Drag/resize SHALL be coalesced. Implementation stays behind `createInlineImageViewer`.

#### Scenario: Open then drag

- **WHEN** the user opens the viewer then drags a zoomed image
- **THEN** the image follows the pointer; content was not fetched while the overlay was closed
- **对应测试**：`tests.md` G4

### Requirement: Dirty library can be reset or repaired explicitly

After the new thumbnail/import path lands, operators SHALL be able to delete the SQLite file and library store (full reset) without this running on every app start. A repair pass SHALL regenerate missing thumbnails or delete the resource package when generation still fails (default: delete).

#### Scenario: Reset after optimization

- **WHEN** the operator runs the documented reset command
- **THEN** the next start is an empty migrated database with an empty store
- **对应测试**：`tests.md` G6
