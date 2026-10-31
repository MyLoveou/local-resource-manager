# Design

## Context

See `proposal.md` for motivation and `docs/requirements/features/library-workspace/设计.md` for the L2 model/interaction contract.

Current state that shapes the implementation:

- `resources.category_id` is a single nullable FK; `categories` is flat with a global unique name.
- Resource list/timeline filters pass a single `categoryId`.
- `/photos` is a separate image+video timeline route; `/image`, `/video`… are separate type routes.
- Collections expose `memberCount` but no preview thumbnails; collection cards are plain boxes.
- Batch mode only toggles by plain click; `selection.selectRange` exists but is unused.
- Home uses `/library/overview` with stats/recent/tasks/work/consumption; no collections/timeline sections.

Constraints:

- SQLite + SQLAlchemy async; migrations are SQL files applied in filename order.
- API JSON is camelCase; frontend HTTP only through `infrastructure/http`.
- Classification MUST remain virtual metadata; physical library paths stay `{type}/{id}`.
- No role/face capability in this change.

## Goals / Non-Goals

**Goals:**

- Per-type category trees with multi-category assignment and subtree filtering.
- A single Library workspace with type tabs, category tree, and grid/timeline/map view switching.
- Saved timeline filters with no member table, type-scoped and multi-category.
- Home dashboard, collection preview cards, batch shortcuts, and clearer operation zones.
- Preserve existing resources, collections, and files through migration.

**Non-Goals:**

- Character/person/face recognition.
- Multi-node category filter in the normal library filter (only saved timelines may use multiple categories).
- Timeline membership tables or manual timeline ordering.
- Physical folder mirroring or moving library files.
- Full MapLibre implementation; map first ships as entry/empty state.
- Pixel-level visual redesign; this change defines information architecture and interaction zones.

## Decisions

### 1. Category tree is per type, multi-category is a join table

- `categories` gains `type`, `parent_id`, `sort`, `is_system`; name unique per `(type, parent_id, name)` with partial unique indexes for roots.
- New `resource_categories(resource_id, category_id)` is the only category membership source. `Resource.categories` is an array.
- `resources.category_id` is migrated, then treated as deprecated read-only for one release; a later migration drops it. This avoids a destructive rebuild in the same release while code stops reading it.
- Tree depth is limited to 4 in the service layer; moves reject cycles; category `type` is immutable.
- Delete: block if children/resources; empty category deletion clears matching IDs from saved-view filters.

**Alternatives:** keep a single FK and add parent_id only (cannot support multi-category); a separate virtual folder entity (duplicates categories/collections); immediate column drop (higher migration risk).

### 2. Subtree filtering is server-side

- `categoryIds` on resource/timeline queries expands each node to its descendants with a recursive CTE; multiple IDs are OR'd and results are deduped.
- A single `categoryId` remains accepted for compatibility and is normalized to a one-element list.
- `uncategorized=true` selects resources with no `resource_categories` rows.
- Tree counts are computed in one aggregate query per type; parent counts use distinct resource IDs, not a sum of child counts.

**Alternatives:** client-side filtering (breaks pagination/counts); storing ancestor rows (write amplification, stale data).

### 3. Timelines are saved filter documents

- `saved_views` stores `kind`, `type`, `name`, `filters_json`, `sort`, timestamps.
- Timeline filters: `categoryIds[]`, `tagIds[]`, `dateFrom`, `dateTo`, `includeUntimed` (default false).
- No member table. Results are computed on read; category deletion removes IDs from filters; an empty category list means "no category condition", not empty results.
- Timeline routes remain type-scoped; image and video timelines are separate.

**Alternatives:** timeline membership table (duplicates collections); storing SQL strings (unsafe/fragile).

### 4. Library workspace uses a new canonical route with redirects

- Canonical route: `/library/:type` with query `view=grid|timeline|map`, `categoryIds`, `tagIds`, `q`, `sort`, `order`, `savedViewId`.
- Old type routes (`/image`, `/video`, …) redirect to `/library/<type>`; `/photos` redirects to `/library/image?view=timeline`.
- `LibraryWorkspace` is the composition root: type tabs, category tree, view switch, filters, and the active view.
- Switching type resets filters and saved-view selection; view mode is retained when supported.
- Collections detail uses `/collections/:id?type=...&view=...`; mixed-type collections show type tabs.

**Alternatives:** keep type routes and add a wrapper (less clean active-menu state); make timeline/map separate routes (contradicts resource-first model).

### 5. Home is an aggregate, collection previews are batched

- Add `GET /library/home` returning: recent resources (12), collection cards with up to 3 preview thumbnails, saved timeline summaries, stats, tasks, active work, recent consumption.
- Extend `CollectionOut` (and mixed collection cards) with `previewThumbnails: string[]`.
- Collection previews use a single window/ranked query per list, not per-collection member calls.
- Home thumbnails open the existing viewer/player for the current item only; no playlist is constructed.

### 6. Batch shortcuts reuse selection state

- `selection.selectRange(orderedIds, toId)` remains the range primitive; ResourceBrowser reads `ctrlKey/shiftKey`, excludes collection cards from the order, and guards editable/overlay targets.
- Shift range replaces selection; plain/Ctrl click toggles; Esc exits batch or closes the top overlay. No Ctrl+A in this version.

### 7. API shape

- `GET /library/categories?type=` → nested nodes with `id/type/parentId/name/sort/count/children`.
- `POST/PATCH/DELETE /library/categories` for management.
- `PATCH /library/resources/{id}` accepts `categoryIds[]`; `Resource.categories` replaces `category`.
- `GET/POST/PATCH/DELETE /library/saved-views?kind=timeline&type=` for timelines.
- `GET /library/home` for the dashboard.
- `GET /library/collections` and resource mixed cards include `previewThumbnails`.

## Risks / Trade-offs

- **[Migration duplicates categories]** Old categories used by multiple types are copied per type; a bug can split memberships. → Migrate on a copied DB, assert resource/category/relation counts, and keep a backup before applying.
- **[Old category column temporarily remains]** Risk of new code accidentally reading it. → Remove all reads/writes in this change; add a test that DTO/query results come from the join; schedule a follow-up drop migration.
- **[Recursive category queries on every page]** Potential cost on large trees. → Index `(parent_id)`, `resource_categories(category_id, resource_id)`; expand descendants once per request; benchmark with a large temp library.
- **[Route churn breaks bookmarks/links]** → Add redirects for old type routes and `/photos`; keep `PhotoDay` working under the canonical type.
- **[Type switch reset expectations]** → Reset all query state; keep view mode only when supported; document in UI.
- **[Collection preview API N+1]** → One batched preview query; cap 3 per collection; cache URLs as existing content endpoints.
- **[Uncommitted R1 work before apply]** → Commit/split existing changes before starting this change; do not mix R1 and workspace migrations in one working tree.
- **[Map scope]** Entry/empty only; no GPS query yet; avoid promising map behavior.

## Migration Plan

1. Back up the library DB and verify a copy opens.
2. `0018_category_tree.sql`: add category tree fields/indexes and `resource_categories`; create the image `待整理分类` system root when needed; backfill memberships from `resources.category_id`, duplicating categories per used type; keep the old column for one release.
3. `0019_saved_views.sql`: create `saved_views`.
4. Deploy backend/UI; verify counts and filters on a temp DB.
5. After one verified release, add a follow-up migration to drop `resources.category_id`.
6. Rollback: restore DB backup and previous app version; no library files were moved.

## Open Questions

None blocking. L3 implementation details are in `docs/requirements/features/library-workspace/实现方案.md`.
