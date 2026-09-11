# desktop-import-entry Specification

## Purpose
Lets the desktop user pick a resource type and local files or a folder, send only those paths to the backend, and watch ingest progress until browse views refresh.

## Requirements

### Requirement: Import wizard is stepped and type-first

The desktop app MUST start import from a toolbar action that opens a wizard: choose an enabled resource type, then choose file or folder, then open a native dialog filtered for that type. File mode MUST allow selecting one file or many files in one dialog. Types without an importer MUST be unavailable. The renderer and the Electron main process MUST NOT copy files into the library store.

#### Scenario: Image file import happy path

- **WHEN** the user chooses Import, type Image, source File, and confirms one image in the native dialog
- **THEN** the app posts that path to the backend import API and does not write the file into the library directory itself

#### Scenario: Multiple files in one file-mode import

- **WHEN** the user chooses file mode and confirms several image files
- **THEN** the app posts all selected paths in one import request

#### Scenario: User cancels the dialog

- **WHEN** the user opens the native picker and cancels
- **THEN** no import request is sent and no error toast is shown

#### Scenario: Disabled type cannot be submitted

- **WHEN** the user is on the type step
- **THEN** types that are not enabled cannot start a picker or POST

### Requirement: Folder pick is a one-shot source

Choosing a folder MUST send that directory path once as `sourceKind=directory`. The UI MUST NOT keep a list of roots or offer Scan Now against previous folders.

#### Scenario: Folder import does not add a root list

- **WHEN** the user imports a folder of images
- **THEN** after completion there is no toolbar or settings list of that folder as a re-scan target

### Requirement: Progress is shown from the backend job

While a job runs, the wizard MUST show progress from GET job (`done`/`total`/`phase`) and MUST prevent starting another import. Failures (400/409/job failed) MUST be visible without `alert` as the only channel. After `done`, image/video grids and home counts MUST refresh without restarting.

#### Scenario: Progress updates during import

- **WHEN** a multi-file import job is running
- **THEN** the UI shows increasing `done` toward `total` or an equivalent phase label from the job payload

#### Scenario: Views refresh after success

- **WHEN** the job status becomes `done` and imported > 0
- **THEN** the matching type grid and home overview counts include the new items without an app restart
