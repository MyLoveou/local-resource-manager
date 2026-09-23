## Purpose

Gives the desktop renderer a stable three-pane shell and a shared selected-resource id so the info pane, grid, and later toolbars see the same current item.

## ADDED Requirements

### Requirement: Shell hosts the info pane

The application chrome SHALL render a right-hand info pane next to the main router view on all primary routes. Resource browsing views MUST NOT embed a second info pane.

#### Scenario: Image route shows one info pane

- **WHEN** the user opens the image library route
- **THEN** exactly one info pane is visible in the application chrome

### Requirement: Selection is shared application state

Clicking a resource card SHALL store that resource id in shared selection state. The info pane SHALL load that resource. If nothing is selected, the info pane SHALL show an empty state and MUST NOT request `/library/resources/undefined`.

#### Scenario: Click selects for the info pane

- **WHEN** the user clicks a resource card with id 12
- **THEN** the info pane displays resource 12

#### Scenario: Empty selection

- **WHEN** no resource is selected
- **THEN** the info pane shows an empty state and does not call the detail API

### Requirement: Soft delete clears selection

When the user confirms delete from the info pane, the client SHALL call `DELETE /library/resources/{id}` and SHALL clear selection on success.

#### Scenario: Delete clears the pane

- **WHEN** delete of the selected resource succeeds
- **THEN** selection is empty and the info pane shows the empty state
