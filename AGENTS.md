# AGENTS.md — UMTX2

Static PS5 jailbreak web host at `document/en/ps5/`. No build system, no TypeScript, no linter, no formatter. Deployed to GitHub Pages via CI.

## Commands
| Command | What it does |
|---|---|
| `npm test` | Full 9-category test suite (Python 3 + Node.js 20 required) |
| `npm run test:js-syntax` | Verbose JS syntax check via `node --check` |
| `npm run test:metadata` | Validates all `payloads/*/metadata.json` |
| `npm run test:payloads` | Payload structure + metadata format only |
| `python3 appcache_manifest_generator.py -d document/en/ps5` | Regenerate offline cache manifest |
| `pip install pyyaml requests` | Required before running `update_payloads.py` locally |
| `python3 .github/scripts/update_payloads.py` | Fetch payloads from GitHub/Gitea releases (needs GH_TOKEN for API) |

## Architecture
- **Entrypoint**: `document/en/ps5/index.html` — script load order IS the dependency graph: `int64.js` → `rop.js` → `main.js` → `umtx2.js` → `syscalls.js` → `psfree/psfree.js` → UI modules → `app.js`.
- **`payload_map.js` is auto-generated** by CI. Do not edit by hand. Source of truth: `.github/payloads.yaml`.
- **Firmware offsets**: 29 files in `document/en/ps5/offsets/` (1.00.js–5.50.js).
- **Source types** in payloads.yaml: `github-release` | `gitea-release` | `direct` | `custom`.
- **License**: The Unlicense (public domain). The `package.json` says MIT erroneously — ignore it.

## Testing quirks
- All tests run from repo root; Python paths derive relative to `document/en/ps5/`.
- CI runs both the test suite AND a separate `node --check` on all JS files.
- CSS validation only checks balanced braces and unclosed comments.
- `appcache-remove` payload is a special case (no binary files, skipped in some tests).

## Gotchas
- `willHideEveryTime: true` hides a payload from the UI every page load (used for deprecated Sonic Loader).
- Konami code (`↑↑↓↓←→←→`) unlocks developer options — not documented in the UI.
- `cache.appcache` is SHA256-hashed; regenerate via `appcache_manifest_generator.py`. It caches only default versions (~60% size savings).
- Plans at `plans/` contain pending feature specs (quick-launch button, cache optimization, etc.).
- Companion Docker self-host repo: `kemalsanli/umtx2-self-hosted`.
