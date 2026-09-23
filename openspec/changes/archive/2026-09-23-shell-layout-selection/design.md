## Context

See proposal.md. Pinia is already registered. `useSelectionStore` exists but is unused. InfoPanel currently requires a `resourceId` prop typed incorrectly.

## Goals / Non-Goals

**Goals:**

- One shell layout for Home / Image / Video
- Shared selected id
- Info pane driven by that id

**Non-Goals:**

- Inline edit form, tag APIs, nested vue-router layouts with named views (a single App shell is enough)

## Decisions

1. **App.vue as the shell, not nested routes**  
   Current routes are flat. Wrapping in a layout component inside App avoids router churn.

2. **Store holds id only**  
   Full resource stays in InfoPanel via GET, so the grid list and detail cannot drift into two sources of truth for fields.

3. **Clear selection on successful delete**  
   Grid still holds trashed-out items until reload; clearing the pane avoids showing a trashed item as current. ResourceBrowser should `reset()` after delete if we can listen — keep it simple: clear selection; optional refresh left to the next visit unless we emit an event.

   After delete, call selection.clear(). ResourceBrowser won't auto-refresh in this change unless we watch store — add a simple `watch` in ResourceBrowser to reset when selectedId becomes null after a delete is too broad.

   Better: InfoPanel emits nothing; ResourceBrowser watches selectedId and if the id disappears from items after delete... items still have the card until reset.

   I'll have InfoPanel call `useResourceHandle().removeResource` then `selection.clear()`, and ResourceBrowser `watch` selectedId: if the deleted id was in items, filter it out or reset(). Simplest: `reset()` on selection clear from delete is wrong for Home.

   ResourceBrowser on delete: listen isn't global. Store can expose `revision` bump. Overkill.

   Minimal: after delete, clear selection; user still sees the card until they re-enter. Spec says pane empty — OK. Optionally filter items in browser if we inject store and remove id from items.

   I'll filter the deleted id out of `items` in ResourceBrowser by watching: when selectedId goes from N to null, don't reset. Cards remain — slight inconsistency.

   Wire: store `lastDeletedId`. ResourceBrowser watches and splices that id. Keep store API: selectedId, select, clear, and `consumeRemovedId`.

   Simplest acceptable: ResourceBrowser watches `selectedId`; InfoPanel after delete calls `clear()`. Cards remain. Spec only requires pane empty. Do that.

## Risks / Trade-offs

- [Home also shows empty info pane] → accepted; keeps chrome stable.  
- [Stale card after delete] → next loadMore/reset; documented as follow-up.

## Migration Plan

Renderer hot reload. No API change.
