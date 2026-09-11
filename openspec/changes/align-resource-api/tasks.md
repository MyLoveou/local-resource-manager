## 1. Backend contract

- [x] 1.1 Add `ResourcePatch` DTO (`title` / `description` / `rating` optional) and verify it round-trips camelCase JSON
- [x] 1.2 Keep `ResourceRepository.update`/`trash`; verify missing id returns None and trash sets `trashed` + `deleted_at`
- [x] 1.3 Add `PATCH`/`DELETE` on `/resources/{resource_id}`, remove `POST /dev/seed` and any `/resource/{id}` routes; verify 404 for missing ids and for `/dev/seed`

## 2. Desktop client

- [x] 2.1 Export `patchResource` and `deleteResource` against `/library/resources/{id}`; verify they use PATCH/DELETE and do not swallow errors
- [x] 2.2 Add or fix `useResourceHandle` so write failures propagate; verify it does not return `null` on error
