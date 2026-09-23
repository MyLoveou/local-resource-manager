## Purpose

修正图片查看器占位、导航控件位置，以及看图时拖拽/窗口缩放的跟手程度。元数据仍在壳右侧信息栏编辑。

## ADDED Requirements

### Requirement: Viewer covers only the main grid pane

When the image viewer is open, it SHALL cover only the shell `main` content (the resource grid). It MUST NOT cover the toolbar, the side menu, or the right-hand metadata panel. The list-page InfoPanel SHALL remain mounted and usable.

#### Scenario: Shell chrome stays

- **WHEN** the user opens the viewer from a selected image
- **THEN** the right metadata panel is still visible and the menu/toolbar remain clickable
- **对应测试**：`tests.md` U1

### Requirement: Navigation controls sit on the image stage

Close SHALL be at the top-right of the image stage. Previous/next SHALL be at the vertical center of the left and right edges of the stage. There MUST NOT be a separate full-width bar of text buttons above the split layout.

#### Scenario: Find close and next

- **WHEN** the viewer is open
- **THEN** close is a control on the image top-right and next/prev are on the image sides
- **对应测试**：`tests.md` U2

### Requirement: Pan and window resize stay in the stage

Panning SHALL move the image inside the main pane without a full-window overlay. Window maximize/restore and continuous resize SHALL update the fitted image without multi-second stalls. Viewer.js remains behind the existing wrapper; `transition` SHALL be off; image switches SHALL NOT destroy/recreate the instance.

#### Scenario: Drag feels attached

- **WHEN** the user drags a zoomed image
- **THEN** the image tracks the pointer inside the main pane (no second full-app layer)
- **对应测试**：`tests.md` U3

### Requirement: Metadata actions use a compact footer

The InfoPanel footer SHALL show at most the primary actions: save, edit, and trash/restore/purge as applicable. Reveal-in-folder, open with default app, open with another app, and change-cover SHALL live under a overflow control labeled 「更多」. This applies on the list page and while the viewer is open (same panel).

#### Scenario: Footer is not a button wall

- **WHEN** an image is selected
- **THEN** the footer does not show all consume buttons in one wrapping row; they are reachable from 「更多」
- **对应测试**：`tests.md` U4
