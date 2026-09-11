# library-ingest Specification

## Purpose
Ingests user-selected local files into an owned library store by copying them into per-resource packages, using pluggable type strategies and reporting job progress.

## Requirements

### Requirement: Import copies into a type-id resource package

The system SHALL copy ingested bytes into `{library_store}/{type}/{id}/` on the backend. The source path SHALL NOT be registered as a persistent library root. The library copy SHALL be the authoritative file for later reads. Identical sha256 already in the library MUST NOT create a second resource or a second copy.

#### Scenario: Single image file is copied

- **WHEN** a client imports `type=image` with `sourceKind=file` and one existing image path
- **THEN** a new image resource exists, a file named as the package primary exists under `library_store/image/{id}/`, and the original file still exists at the source path

#### Scenario: Directory is not remembered as a root

- **WHEN** a client imports `type=image` with `sourceKind=directory` and a folder path
- **THEN** matching images are ingested and no API thereafter lists that folder as a library root to scan again

#### Scenario: Duplicate hash is skipped

- **WHEN** the same file bytes are imported a second time
- **THEN** `skippedDuplicate` increases and no additional resource package is created

### Requirement: Type strategies control what is collected and stored

The system SHALL select files by the requested `type` extension list. Package paths MUST be produced by the shared package/layout module, not by ad-hoc string concatenation in an importer. Image packages MUST contain a primary file; `resolve_cover` MUST return that primary when no dedicated cover role exists. Video ingest in this change MUST copy only the primary file (no subtitles, no generated cover). Author or category MUST NOT determine the physical folder tree. Unknown or disabled types MUST be rejected with HTTP 400.

#### Scenario: Image folder ignores non-images

- **WHEN** a directory containing images and unrelated files is imported as `type=image`
- **THEN** only image extensions become resources

#### Scenario: Image cover falls back to primary

- **WHEN** an image has been imported with only a primary file
- **THEN** cover resolution returns that primary file (no second cover copy is required)

#### Scenario: Video ingest is primary only

- **WHEN** a video file `foo.mp4` is imported and `foo.srt` sits in the same source directory
- **THEN** the resource package contains the primary video and MUST NOT copy the subtitle in this change

#### Scenario: Unsupported type is rejected

- **WHEN** a client posts an import with a type that has no enabled importer
- **THEN** the system returns HTTP 400 and copies nothing

### Requirement: Backend owns IO metadata and exclusive jobs

The system SHALL hash, copy, probe metadata, and write the database only in the backend process. File copy, move, and rename used by ingest MUST go through a shared file-operations module. At most one import job SHALL run; a second create request MUST return HTTP 409. Unreadable files MUST increment `skippedError` without aborting the rest of the job.

#### Scenario: Concurrent import is rejected

- **WHEN** an import job is running and another POST import is sent
- **THEN** the second request returns HTTP 409

#### Scenario: Unreadable file is counted

- **WHEN** one candidate cannot be read and others can
- **THEN** readable items ingest and `skippedError` is at least 1

### Requirement: Import is a job with observable progress

POST `/library/imports` SHALL accept `{ type, sourceKind, paths }` and return HTTP 202 with `jobId`. GET `/library/imports/{jobId}` SHALL return `status`, `phase`, `total`, `done`, and count fields. Content endpoints SHALL stream library copies by resource id (and file id for non-primary), never by a raw filesystem query parameter.

#### Scenario: Job is created and reaches done

- **WHEN** a valid import POST is accepted
- **THEN** the client can GET the job until `status` is `done` or `failed` and `done` never exceeds `total`

#### Scenario: Content is served from the library copy

- **WHEN** an imported image content URL is requested
- **THEN** the body is the copied file bytes from the library store

#### Scenario: Unknown content id is 404

- **WHEN** content is requested for a missing resource id
- **THEN** the response is HTTP 404
