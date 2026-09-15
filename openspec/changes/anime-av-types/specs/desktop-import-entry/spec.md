## MODIFIED Requirements

### Requirement: Progress is shown from the backend job

While a job runs, the wizard MUST show progress from GET job (`done`/`total`/`phase`) and MUST prevent starting another import. Failures (400/409/job failed) MUST be visible without `alert` as the only channel. After `done`, the grid for the imported type (image, video, or anime/av **works**) and home counts MUST refresh without restarting.

#### Scenario: Progress updates during import

- **WHEN** a multi-file import job is running
- **THEN** the UI shows increasing `done` toward `total` or an equivalent phase label from the job payload
- **对应测试**：`tests.md` R1

#### Scenario: Views refresh after success

- **WHEN** the job status becomes `done` and imported > 0
- **THEN** the matching type grid and home overview counts include the new items without an app restart
- **对应测试**：`tests.md` T4
