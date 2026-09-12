## Purpose

浏览与看图的加载、词表、缓存、前后端查询与手势性能。

## ADDED Requirements

### Requirement: Off-screen images are lazy

Grid card images SHALL use lazy loading (or equivalent). Original `/content` MUST NOT be requested until the image viewer is open for that resource.

#### Scenario: Scroll grid

- **WHEN** the user scrolls the image page
- **THEN** only visible (plus virtualizer overscan) card images start loading
- **对应测试**：`tests.md` P4

### Requirement: Metadata panel preview is a thumbnail

The InfoPanel and edit-modal preview image SHALL use `thumbnailPath` when present, not the original `coverPath`/`content`. Opening the viewer still uses original content.

#### Scenario: Select a card

- **WHEN** the user selects an image with a thumbnail
- **THEN** the panel preview request is the thumbnail URL
- **对应测试**：`tests.md` P5

### Requirement: Vocab fetch does not block first paint

Loading categories or tags SHALL NOT delay the resource grid first paint. InfoPanel title and description SHALL render without waiting for vocab lists.

#### Scenario: Open image page

- **WHEN** the user opens the image route
- **THEN** the grid appears even if `/library/categories` is still in flight
- **对应测试**：`tests.md` P6

### Requirement: Short-lived caches

`getResource` and vocab lists SHALL be cached in memory until `library.bump` or an explicit invalidate after vocab-changing saves. Thumbnail and content HTTP responses SHALL include Cache-Control.

#### Scenario: Reselect same id

- **WHEN** the user selects the same resource again before any library bump
- **THEN** the panel does not wait on a duplicate detail GET
- **对应测试**：`tests.md` P7

### Requirement: Backend hydrate is not N sequential queries

Resource detail loading SHALL load category, tags, files, and todos without a query-per-relation round trip.

#### Scenario: GET detail

- **WHEN** `GET /library/resources/{id}` runs
- **THEN** associated rows are loaded in a batched/joined fashion
- **对应测试**：`tests.md` P8

### Requirement: Pan, zoom, and window resize stay responsive

Dragging a zoomed image SHALL follow the pointer. Window maximize/resize SHALL refit without a multi-second blank. Resize work SHALL be coalesced.

#### Scenario: Drag and maximize

- **WHEN** the user zooms, drags, then maximizes
- **THEN** P1/P2 in tests.md hold
- **对应测试**：`tests.md` P1 P2
