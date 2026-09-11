## 1. Shared file ops and store layout

- [x] 1.1 Add `FileOps` (copy/move/rename) under `app/shared/fs` and verify importer tests call it rather than raw shutil in the import service
- [x] 1.2 Add `ResourcePackage` (`ensure_dir`, `put_primary`, `put_cover`, `put_role`, `resolve_cover`) and per-type Layouts; verify importers do not concatenate `{type}/{id}` themselves and image cover falls back to primary
- [x] 1.3 Add migration `files.role` default `primary`; verify existing rows (if any) remain readable
- [x] 1.4 Keep library store location as an implementation default beside current DB data (no settings API); verify no user-facing library-path setting is added

## 2. Backend ingest job

- [x] 2.1 Implement image importer and a video importer that only places primary; verify a mixed folder with `type=image` ignores non-images and a sibling `.srt` is not copied for video
- [x] 2.2 Implement ImportService: hash, skip duplicate sha256, copy via FileOps, write resource+files, probe metadata on backend; verify a second ingest of the same bytes does not add a package
- [x] 2.3 Add POST `/library/imports` (202 jobId) and GET job progress; verify 400 for empty paths/disabled type, 409 when a job is running, and `done`/`total`/`phase` update
- [x] 2.4 Stream content from library copies by id; verify query-string disk paths are not accepted and missing ids return 404
- [x] 2.5 Skip demo seed on newly created databases; verify a fresh DB has zero resources

## 3. Desktop wizard

- [x] 3.1 Expose native file (single or multi) and directory pickers that return paths only; verify cancel returns empty/null and no copy occurs in main/renderer
- [x] 3.2 Build type-first wizard (type → file/folder → dialog → progress from GET job); verify disabled types cannot POST and folder import does not create a roots UI
- [x] 3.3 After job `done`, bump library revision so grids and Home refetch; verify new items appear without restart

## 4. Verification gate

- [x] 4.1 Run `tests.md` mapped cases plus `pnpm --filter desktop typecheck`; verify listed automated IDs pass
