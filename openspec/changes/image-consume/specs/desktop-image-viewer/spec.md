## Purpose

Defines when the desktop opens an in-app image viewer overlay, how the original image is shown with zoom and adjacent navigation, and that metadata editing remains available while viewing.

## ADDED Requirements

### Requirement: Second click on a selected image opens the viewer

When not in batch-delete mode, a click on an already-selected image card SHALL open the image viewer overlay. A click on a not-yet-selected card SHALL only select it. Double-click on an image card SHALL also open the viewer. Video cards MUST NOT open this viewer.

#### Scenario: Select then open

- **WHEN** the user clicks an unselected image card then clicks the same card again
- **THEN** the overlay opens with that resource
- **对应测试**：`tests.md` T1

#### Scenario: Batch mode does not open

- **WHEN** batch-delete mode is on and the user clicks a selected image card
- **THEN** the overlay does not open
- **对应测试**：`tests.md` T2

### Requirement: Description can be saved while viewing

While the viewer is open, the shell info panel SHALL still save description. Escape SHALL close the viewer without changing the shell route. Layout is defined by `desktop-image-viewer` in the archived `image-viewer-ux` change.

#### Scenario: Edit description while viewing

- **WHEN** the viewer is open and the user saves a new description
- **THEN** GET of that resource returns the new description
- **对应测试**：`tests.md` T3

### Requirement: Viewer supports complete viewing gestures

The right-hand viewer SHALL support zoom, pan, rotate, fit-to-view, actual size, and fullscreen, using an integrated complete viewer (assumed Viewer.js unless replaced). Keyboard left/right SHALL move to the previous/next **image** in the currently loaded grid list.

#### Scenario: Zoom and next image

- **WHEN** the overlay is open and the user zooms then goes to the next image
- **THEN** the next loaded image is shown and zoom can be applied again
- **对应测试**：`tests.md` T4
