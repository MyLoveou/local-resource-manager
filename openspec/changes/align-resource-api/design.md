## Context

See proposal.md for motivation. Today `GET/POST` live on `/library/resources`. Incomplete write routes on `/library/resource/{id}` must not ship. `ResourceRepository` already has draft `update`/`trash` on this branch. Soft-delete exists as `Resource.to_trash()`. Lifespan already seeds an empty database.

## Goals / Non-Goals

**Goals:**

- One noun path for the resource collection
- Writes that persist and match the status machine
- Frontend HTTP that hits the same URLs and surfaces errors

**Non-Goals:**

- API version prefix, token verification, APIRouter split, InfoPanel wiring, nested app shell

## Decisions

1. **PATCH instead of PUT**  
   PUT with a full `Resource` invites overwriting `id`/`createdAt`/`status`. PATCH with `title` / `description` / `rating` matches info-panel edits.  
   Alternative: PUT full resource — rejected.

2. **DELETE means trash, not row removal**  
   Product already has `trashed` / restore. Returning the trashed resource lets the UI drop it from the active grid.  
   Alternative: `POST /resources/{id}/trash` — extra path; keep DELETE as "remove from library view".

3. **Remove HTTP seed**  
   Startup `seed_demo_if_empty` is enough. A public seed POST is a footgun.

4. **Keep `Resource` in shared models**  
   Moving the domain type belongs to the router-assembly change.

## Risks / Trade-offs

- [Clients calling `/library/resource/{id}`] → none in production; no alias.  
- [DELETE on already-trashed] → idempotent 200, skip `InvalidStateError`.  
- [PATCH does not change `status`] → status changes only via delete (trash) for now.

## Migration Plan

Ship backend and desktop together. No DB migration. Rollback is reverting the branch merge.
