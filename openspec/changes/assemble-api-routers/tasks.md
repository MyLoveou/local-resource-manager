## 1. Library routers

- [x] 1.1 Extract session/repo Depends into `library/api/deps.py` and verify routes still obtain an AsyncSession
- [x] 1.2 Split health, overview, and resources into `APIRouter` modules assembled by `library/api/router.py`; verify `/library/resources` and `/library/health` still 200

## 2. Root assembly

- [x] 2.1 Convert scrape and download to `APIRouter` with health only; verify `/scrape/health` and `/download/health` still 200
- [x] 2.2 Replace `app.mount` in `main.py` with `include_router` prefixes; verify `/health` plus the three module health paths
