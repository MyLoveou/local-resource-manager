# Vue Security

> Extends `typescript-security` and `common-security`.

## XSS

- **`v-html`**: CRITICAL — sanitize user HTML (DOMPurify) or forbid
- **Dynamic attribute binding**: validate URLs before `href` / `src`
- **Template injection**: never compile user-controlled template strings

## Client secrets

- Only `VITE_*` (or project public prefix) in client code
- No API keys, private tokens, or admin credentials in `.vue` or client bundles

## Auth

- Session tokens in httpOnly cookies, not `localStorage`
- Router guards must mirror API authorization rules

## Dependencies

- Audit UI library versions; prefer maintained component libraries
- Avoid loading third-party scripts in SFC without CSP review

