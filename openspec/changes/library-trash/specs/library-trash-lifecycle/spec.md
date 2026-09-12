## Purpose

Defines HTTP and storage behavior for moving library resources into trash, restoring them, and permanently removing both the database row and the on-disk resource package.

## ADDED Requirements

### Requirement: Soft delete remains the default HTTP delete

`DELETE /library/resources/{id}` SHALL mark the resource `trashed` and set `deletedAt`. The system MUST NOT drop the row or delete the on-disk package. Unknown ids MUST yield HTTP 404. An already-trashed resource MUST remain trashed and still return HTTP 200.

#### Scenario: Active resource is trashed

- **WHEN** a client sends `DELETE /library/resources/{id}` for an active resource
- **THEN** the system returns HTTP 200, `status` is `trashed`, and `deletedAt` is set
- **对应测试**：`tests.md` T1

#### Scenario: Trash is idempotent

- **WHEN** a client sends `DELETE /library/resources/{id}` for a resource already `trashed`
- **THEN** the system returns HTTP 200, the resource stays `trashed`, and the package remains on disk
- **对应测试**：`tests.md` T2

### Requirement: Restore returns a trashed resource to active

`POST /library/resources/{id}/restore` SHALL set `status` to `active` and clear `deletedAt` when the resource is `trashed`. Unknown ids MUST yield HTTP 404. Restoring a non-trashed resource MUST yield HTTP 409 (or the documented client error) and MUST NOT change status.

#### Scenario: Trashed resource is restored

- **WHEN** a client sends `POST /library/resources/{id}/restore` for a trashed resource
- **THEN** the system returns HTTP 200, `status` is `active`, and `deletedAt` is null
- **对应测试**：`tests.md` T3

#### Scenario: Restore missing id

- **WHEN** a client sends `POST /library/resources/{id}/restore` for an unknown id
- **THEN** the system returns HTTP 404
- **对应测试**：`tests.md` T4

### Requirement: Purge deletes the package then the row

`POST /library/resources/{id}/purge` SHALL delete the library resource package directory when it exists, then DROP the resource row (CASCADE files/todos/tags). The system MUST NOT delete the user's original import source file. If the package is already missing, the system MAY still DROP the row. If package deletion fails, the system MUST NOT DROP the row and MUST return a client-visible error.

#### Scenario: Purge removes row and package

- **WHEN** a client sends `POST /library/resources/{id}/purge` for a stored resource that has a package
- **THEN** the resource id is gone from GET, and `{library}/{type}/{id}/` does not exist
- **对应测试**：`tests.md` T5

#### Scenario: Purge does not touch the import source

- **WHEN** a resource was imported by copying from a source path that still exists
- **THEN** after purge the source path still exists
- **对应测试**：`tests.md` T6

### Requirement: Trash list omits type filter

`GET /library/resources?status=trashed` SHALL return trashed resources of all types when `type` is omitted.

#### Scenario: Mixed types in trash list

- **WHEN** the library has a trashed image and a trashed video
- **THEN** `GET /library/resources?status=trashed` includes both ids in `items`
- **对应测试**：`tests.md` T7

### Requirement: Batch actions report partial success

`POST /library/resources/batch` SHALL accept `{ action: "trash"|"restore"|"purge", ids: number[] }` with unique ids, maximum 200. Each id SHALL be processed independently. The response SHALL be `{ ok: number[], failed: { id: number, message: string }[] }`. Trash and restore of an already-correct status SHALL count as `ok`. Restore of a non-trashed id SHALL count as `failed`. Unknown ids for restore/purge SHALL count as `failed`. Invalid action or more than 200 ids SHALL yield HTTP 422.

#### Scenario: Batch trash mixed results

- **WHEN** a client sends batch `trash` with one valid id and one unknown id
- **THEN** the valid id is `trashed` and listed in `ok`, and the unknown id is listed in `failed`
- **对应测试**：`tests.md` T8

#### Scenario: Batch exceeds limit

- **WHEN** a client sends more than 200 ids
- **THEN** the system returns HTTP 422 and does not change any resource
- **对应测试**：`tests.md` T9
