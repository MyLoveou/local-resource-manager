## Purpose

Defines the desktop trash view, multi-select batch actions, confirmation dialogs, and keeping the visible grid in sync with the library after trash, restore, or purge.

## ADDED Requirements

### Requirement: Trash route lists trashed resources

The desktop SHALL expose a sidebar item that navigates to `/trash`. That view SHALL list resources with `status=trashed` in the virtual grid and SHALL allow the info panel to show a selected trashed item including `deletedAt`.

#### Scenario: Open trash from the sidebar

- **WHEN** the user opens 回收站
- **THEN** the route is `/trash` and the grid requests a trashed list (not the active image/video list)
- **对应测试**：`tests.md` T10

### Requirement: Batch mode then confirm delete

The type-page grid SHALL NOT enter multi-select via Ctrl/Shift in the default browse mode. The user SHALL click 批量删除 to enter batch mode. In batch mode, a click on a card SHALL toggle selection. The 移入回收站 action SHALL be visible only in batch mode and SHALL require confirmation. 取消 SHALL leave batch mode without changing the library.

#### Scenario: Batch delete mode on the image page

- **WHEN** the user clicks 批量删除, toggles two cards, then confirms 移入回收站
- **THEN** both resources are trashed and the type page leaves batch mode
- **对应测试**：`tests.md` T11

#### Scenario: Browse click does not show batch delete action

- **WHEN** the user has not entered batch mode and clicks a card
- **THEN** the info panel shows that resource and 移入回收站 for the batch bar is not shown
- **对应测试**：`tests.md` T11b

### Requirement: Destructive actions require confirmation

Moving to trash, restoring, purging, and emptying trash SHALL show a confirmation dialog. Cancel MUST leave the library unchanged. Purge and empty-trash copy MUST state that the action cannot be undone.

#### Scenario: Cancel trash confirmation

- **WHEN** the user starts 移入回收站 and cancels the dialog
- **THEN** the resource stays `active` and remains on the type page
- **对应测试**：`tests.md` T12

### Requirement: Grid matches library after mutations

After a successful trash, restore, or purge (single or batch), the currently visible grid MUST no longer show ids that left that view and MUST show ids that entered that view without requiring an app restart.

#### Scenario: Trash removes the card from the type page

- **WHEN** the user confirms trash on a selected card on the image page
- **THEN** that card disappears from the image grid and appears in 回收站
- **对应测试**：`tests.md` T13

#### Scenario: Restore returns the card to its type page

- **WHEN** the user confirms restore on a trashed card
- **THEN** the card disappears from 回收站 and appears on the matching type page
- **对应测试**：`tests.md` T14

### Requirement: Trash panel actions are restore and purge

On `/trash`, the info panel MUST offer 恢复 and 彻底删除, and MUST NOT offer 移入回收站. On type pages, the panel MUST offer 移入回收站 for active resources.

#### Scenario: Panel buttons follow status

- **WHEN** an active image is selected then a trashed item is selected
- **THEN** the panel switches from 移入回收站 to 恢复 and 彻底删除
- **对应测试**：`tests.md` T15

### Requirement: Empty trash purges remaining items

The trash view SHALL offer 清空回收站. After confirmation the system SHALL purge remaining trashed resources (paging/batching as needed) until the trash list is empty.

#### Scenario: Empty trash

- **WHEN** trash contains multiple items and the user confirms 清空回收站
- **THEN** the trash grid is empty and those packages are gone from disk
- **对应测试**：`tests.md` T16
