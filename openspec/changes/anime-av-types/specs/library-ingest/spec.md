## MODIFIED Requirements

### Requirement: Type strategies control what is collected and stored

The system SHALL select files by the requested `type` extension list. Package paths MUST be produced by the shared package/layout module, not by ad-hoc string concatenation in an importer. Image packages MUST contain a primary file; `resolve_cover` MUST return that primary when no dedicated cover role exists. Video ingest (`type=video`) MUST copy only the primary file (no subtitles, no generated cover). Types `anime` and `av` MUST use series ingest (preview then one work package) rather than one-file-one-resource. Source folder layout MUST NOT be mirrored as-is; confirmed mapping MUST land in the canonical `SxxExx` tree. Author or category MUST NOT determine the physical folder tree. Unknown or disabled types MUST be rejected with HTTP 400.

#### Scenario: Image folder ignores non-images

- **WHEN** a directory containing images and unrelated files is imported as `type=image`
- **THEN** only image extensions become resources
- **对应测试**：`tests.md` R1

#### Scenario: Image cover falls back to primary

- **WHEN** an image has been imported with only a primary file
- **THEN** cover resolution returns that primary file (no second cover copy is required)
- **对应测试**：`tests.md` R1

#### Scenario: Video ingest is primary only

- **WHEN** a video file `foo.mp4` is imported as `type=video` and `foo.srt` sits in the same source directory
- **THEN** the resource package contains the primary video and MUST NOT copy the subtitle in this change
- **对应测试**：`tests.md` R1

#### Scenario: Unsupported type is rejected

- **WHEN** a client posts an import with a type that has no enabled importer
- **THEN** the system returns HTTP 400 and copies nothing
- **对应测试**：`tests.md` T4
