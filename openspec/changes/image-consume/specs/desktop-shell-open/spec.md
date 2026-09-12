## Purpose

Defines how the desktop reveals a library file in the OS file manager and how it opens that file with the operating system's default application, without giving the renderer Node filesystem access.

## ADDED Requirements

### Requirement: Reveal primary in the file manager

The desktop SHALL offer 打开所在位置 for an image whose primary file path is known. The action SHALL call the main-process shell to show that file in the folder. The path MUST be the library copy, not a remembered import source. Missing files MUST show a failure message and MUST NOT crash the app.

#### Scenario: Reveal existing package file

- **WHEN** the user confirms 打开所在位置 for an imported image
- **THEN** the OS file manager opens the folder containing `{library}/image/{id}/primary.*` and the file is selected when the OS supports it
- **对应测试**：`tests.md` T5

### Requirement: Open with the default external application

The desktop SHALL offer 用外部应用打开, which SHALL ask the main process to open the primary path with the OS default handler (`shell.openPath`). The renderer MUST NOT call Node `fs` or `child_process`.

#### Scenario: Open with default app

- **WHEN** the user chooses 用外部应用打开 for an imported image
- **THEN** the OS default application starts on that library file
- **对应测试**：`tests.md` T6

### Requirement: User can pick a different application

The desktop SHALL offer 选择其他应用. The main process SHALL open the OS “Open with” flow when the platform provides one (Windows Open As), or let the user pick an application/executable and launch it with the file path as an argument. The renderer MUST NOT concatenate the path into a shell command string.

#### Scenario: Choose another app

- **WHEN** the user chooses 选择其他应用 and picks a handler
- **THEN** that handler opens the same library primary file
- **对应测试**：`tests.md` T6b

### Requirement: Main process rejects missing paths

IPC handlers MUST no-op or return an error when the path is not an existing file.

#### Scenario: Missing file

- **WHEN** IPC is invoked with a path that does not exist
- **THEN** the handler does not throw uncaught in main, and the UI can show failure
- **对应测试**：`tests.md` T7
