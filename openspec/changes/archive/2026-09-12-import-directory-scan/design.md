## Context

See proposal.md. Current code can POST a resource row but never copies files and never writes `files`. The renderer has no folder/file picker. Demo seed fills new DBs. Previous draft registered `library_roots` and linked `files.path` to the user's original disk; that draft is withdrawn.

## Goals / Non-Goals

**Goals:**

- Encapsulated package layout: shared role helpers (`put_primary`, `put_cover`, `resolve_cover`) plus per-type layouts
- Image + video enabled; video extras (subtitles, poster probe) deferred
- Shared `FileOps`; job progress; `files.role` for current primary and future cover/sidecars
- File picker allows one or many paths

**Non-Goals:**

- Watcher, persistent roots, Scan Now, `/v1`, token checks, ffmpeg, author-based folders, renderer filesystem writes, settings UI for library path, video sidecar ingest, clearing old demo rows

## Decisions

1. **Copy, do not link**  
   Library must survive source moves.  
   Alternative: symlink — rejected.

2. **ResourcePackage + type Layouts**  
   `{type}/{id}/` on disk. Shared methods for roles many types share (cover). Importers must not concatenate store paths. Image: `cover_falls_back_to_primary`. Video this slice: `put_primary` only.  
   Alternative: each importer invents folders — rejected.

3. **Job + polling, not a long POST**  
   In-memory single job is enough this slice.  
   Alternative: SSE / persisted jobs — later.

4. **IPC returns paths only**  
   Native dialog; backend copies.

5. **`files.role` migration**  
   `primary` now; `cover` / sidecars later without a new fork.

6. **Library root path is not a setting this change**  
   Code may place the store beside the existing DB file. The settings module will own userData / user-visible path later.

7. **Skip demo seed on new DBs only**  
   Leave existing demo rows.

## Risks / Trade-offs

- [Copy doubles disk] → accepted.  
- [In-memory job dies with backend] → user re-imports.  
- [Video grid has no poster] → accepted until the video-special change.  
- [Hard-coded store next to DB] → temporary; settings will replace it.

## Migration Plan

Add `0002_file_role.sql`. No settings migration. Rollback: revert the branch.

## Open Questions

None. Closed in 需求.md §9.
