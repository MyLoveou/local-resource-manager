## Purpose

Defines the HTTP contract for library resources: listing with a page envelope, fetching one item, partial update, and soft-delete into trash.

## ADDED Requirements

### Requirement: Resource collection uses a stable plural path

The system SHALL expose the resource collection at `/library/resources` and a single resource at `/library/resources/{id}`. The system MUST NOT serve `/library/resource/{id}`.

#### Scenario: List uses plural collection path

- **WHEN** a client requests `GET /library/resources`
- **THEN** the system returns HTTP 200 with a page envelope containing `items`, `total`, `limit`, `offset`, and `hasMore`

#### Scenario: Singular path is not found

- **WHEN** a client requests `PUT` or `DELETE` on `/library/resource/{id}`
- **THEN** the system returns HTTP 404

### Requirement: Single resource read

The system SHALL return the resource for `GET /library/resources/{id}` when it exists, including trashed resources. The system SHALL return HTTP 404 when it does not exist.

#### Scenario: Existing resource

- **WHEN** a client requests `GET /library/resources/{id}` for a stored id
- **THEN** the system returns HTTP 200 and the resource body

#### Scenario: Missing resource

- **WHEN** a client requests `GET /library/resources/{id}` for an unknown id
- **THEN** the system returns HTTP 404

### Requirement: Partial update

The system SHALL accept `PATCH /library/resources/{id}` with a body that may include `title`, `description`, and `rating` only. Omitted fields MUST remain unchanged. Unknown ids MUST yield HTTP 404.

#### Scenario: Patch title only

- **WHEN** a client sends `PATCH /library/resources/{id}` with `{ "title": "New" }`
- **THEN** the stored title is "New" and other fields are unchanged

#### Scenario: Patch missing id

- **WHEN** a client sends `PATCH /library/resources/{id}` for an unknown id
- **THEN** the system returns HTTP 404

### Requirement: Soft delete moves the resource to trash

`DELETE /library/resources/{id}` SHALL mark the resource `trashed` (soft delete) using the resource status machine and MUST return the updated resource. The system MUST NOT hard-delete the row. Unknown ids MUST yield HTTP 404. A resource that is already trashed MUST remain trashed and still return HTTP 200 with the current representation.

#### Scenario: Active resource is trashed

- **WHEN** a client sends `DELETE /library/resources/{id}` for an active resource
- **THEN** the system returns HTTP 200, `status` is `trashed`, and `deletedAt` is set

#### Scenario: Delete missing id

- **WHEN** a client sends `DELETE /library/resources/{id}` for an unknown id
- **THEN** the system returns HTTP 404

### Requirement: Demo seed is not a public HTTP command

The system MUST NOT expose `POST /library/dev/seed` as a client API. Empty-database seeding MAY still run at process startup.

#### Scenario: Seed endpoint gone

- **WHEN** a client requests `POST /library/dev/seed`
- **THEN** the system returns HTTP 404

### Requirement: Desktop client follows the same contract

The desktop HTTP client SHALL call `/library/resources` and `/library/resources/{id}` for list, get, patch, and delete. Write failures MUST propagate to the caller.

#### Scenario: Delete uses plural path

- **WHEN** the desktop deletes a resource
- **THEN** it sends `DELETE /library/resources/{id}`

#### Scenario: Write error is not swallowed

- **WHEN** a patch or delete request fails
- **THEN** the caller receives a rejected promise or thrown error rather than `null`
