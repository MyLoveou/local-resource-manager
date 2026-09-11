## Context

See proposal.md. Today `main.py` mounts three FastAPI instances. library `routes.py` holds health, overview, CRUD, and (removed) seed. Frontend already calls `/library/resources`.

## Goals / Non-Goals

**Goals:**

- One ASGI app, `APIRouter` + `include_router`
- Split library routes by concern without changing JSON contracts
- Same pattern for empty scrape/download routers

**Non-Goals:**

- `/api/v1`, auth middleware, frontend layout, moving `Resource` out of `shared/models`

## Decisions

1. **`include_router(prefix="/library")` over `mount`**  
   Same process and DB; mount's isolated OpenAPI is cost without benefit.

2. **Split files: `health.py`, `overview.py`, `resources.py`, aggregate `router.py`**  
   Delete the fat `routes.py` after the move. Shared `_service` Depends lives in a small `deps.py`.

3. **Keep `root_path` unused**  
   It was for mounted sub-apps. Root OpenAPI will list `/library/resources` as full paths.

## Risks / Trade-offs

- [Clients using `/library/docs`] → only local; root `/docs` is the replacement.  
- [Import cycles] → deps.py only imports session + repositories.

## Migration Plan

Single deploy. Rollback by reverting the merge. No DB change.

## Open Questions

None.
