## 1. Shell

- [x] 1.1 Move InfoPanel into App chrome beside `router-view` and remove it from ResourceBrowser; verify Image/Video show a single right pane
- [x] 1.2 Drive InfoPanel from `useSelectionStore` (optional id); verify no detail request when selection is null

## 2. Selection and delete

- [x] 2.1 ResourceBrowser card click calls `select(id)` and drops local activated ref; verify clicking a card updates the pane
- [x] 2.2 InfoPanel delete uses `useResourceHandle` then `clear()`; verify a failed delete keeps the current selection
