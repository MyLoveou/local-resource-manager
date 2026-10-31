# backend-access-control Specification

## Purpose

Defines how the local backend authorizes requests when the desktop shell injects a per-launch bearer token, and which paths stay reachable without a request header (health probes, API docs, and media bytes consumed by `img`/`video`/`model-viewer`).

## Requirements

### Requirement: Protected routes require a bearer token

When a token is configured, the backend SHALL require `Authorization: Bearer <token>` on every path that is not exempt, and SHALL reject requests with a wrong or missing token using HTTP 401 and the project's standard JSON envelope (`status=error`, `code=401`). Token comparison SHALL NOT be a plain string equality.

#### Scenario: Missing header

- **WHEN** a client calls `GET /library/resources` without an `Authorization` header and a token is configured
- **THEN** the response is 401 with envelope `code=401`, `status=error`
- **对应测试**：`tests.md` T1

#### Scenario: Wrong token

- **WHEN** a client calls `GET /library/resources` with `Authorization: Bearer wrong`
- **THEN** the response is 401
- **对应测试**：`tests.md` T2

#### Scenario: Correct token

- **WHEN** a client calls `GET /library/resources` with the configured token
- **THEN** the response is 200 and the body is unchanged from today's contract
- **对应测试**：`tests.md` T3

#### Scenario: Token value never logged

- **WHEN** a request is rejected for a bad token
- **THEN** the log line contains only method and path, never the received token value
- **对应测试**：`tests.md` T7

### Requirement: Exempt paths are declared centrally

The set of paths that bypass token validation SHALL live in one constant module, not in per-route conditionals, and SHALL cover health probes and the OpenAPI documents.

#### Scenario: Backend health without a token

- **WHEN** a client calls `GET /health` or `GET /library/health` without a token
- **THEN** the response is 200
- **对应测试**：`tests.md` T4

#### Scenario: API docs without a token

- **WHEN** a client calls `GET /openapi.json` without a token
- **THEN** the response is 200 and is not wrapped in the envelope
- **对应测试**：`tests.md` T5

### Requirement: Media byte streams stay reachable without a header

Paths serving media bytes SHALL be exempt from token validation because `img`, `video`, and `model-viewer` cannot attach an `Authorization` header. This exemption SHALL be limited to byte-stream endpoints (`*/content`) and the scrape image proxy.

#### Scenario: Thumbnail and content read

- **WHEN** a client calls `GET /library/resources/{id}/content` or `GET /library/resources/{id}/files/{fileId}/content` without a token
- **THEN** the response is not 401 (it is the normal 200 or 404 for that resource)
- **对应测试**：`tests.md` T6

#### Scenario: List and detail stay protected

- **WHEN** a client calls `GET /library/resources` without a token
- **THEN** the response is 401 — the exemption does not widen to the collection endpoint
- **对应测试**：`tests.md` T1

### Requirement: CORS preflight is never blocked by token validation

Because browsers never attach credentials to a CORS preflight, the backend SHALL let `OPTIONS` reach the CORS layer, and every response — including 401 — SHALL carry CORS headers.

#### Scenario: Browser preflight

- **WHEN** the renderer at a different origin sends `OPTIONS /library/overview` with `Access-Control-Request-Method` and `Access-Control-Request-Headers: authorization`, and a token is configured
- **THEN** the response is 200 with `access-control-allow-origin`, so the browser proceeds to send the real request
- **对应测试**：`tests.md` T12

#### Scenario: Unauthorized response is readable by the renderer

- **WHEN** a protected request without a valid token is sent with an `Origin` header
- **THEN** the 401 response still carries `access-control-allow-origin`, so the renderer reports 401 instead of a generic network error
- **对应测试**：`tests.md` T13

### Requirement: No token configured means auth is disabled and logged

When no token is configured (for example a bare `pnpm backend:start`), the backend SHALL serve requests without authorization and SHALL log a startup warning naming the reason. The Electron path always injects a token, so the shipped app runs with validation on.

#### Scenario: Bare development server

- **WHEN** the backend starts with an empty token
- **THEN** a warning is logged and `GET /library/resources` without a header returns 200
- **对应测试**：`tests.md` T8

#### Scenario: Environment mapping works

- **WHEN** `BACKEND_TOKEN` is set in the environment
- **THEN** `settings.token` equals that value
- **对应测试**：`tests.md` T9
