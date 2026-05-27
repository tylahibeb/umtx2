# Spec: Add Elf Arsenal as second payload + deprecate Sonic Loader

**Status:** ✅ Implemented
**Date:** 2026-05-27
**Request:** Add https://git.etawen.dev/soniciso/elf-arsenal/releases as the second payload

---

## 1. Summary

Add **Elf Arsenal** (by maj0r/soniciso) as a `gitea-release` sourceType payload, placed **second** (after pldmgr) in the payload list. It's the official successor to Sonic Loader (already in the codebase), which is marked deprecated (hidden from UI). The repo is on a Gitea instance (git.etawen.dev), not GitHub — a new `gitea-release` sourceType was added to `update_payloads.py` to support dynamic latest-release fetching via the Gitea REST API.

---

## 2. Source Repository

| Field | Value |
|-------|-------|
| **URL** | https://git.etawen.dev/soniciso/elf-arsenal |
| **Releases API** | https://git.etawen.dev/api/v1/repos/soniciso/elf-arsenal/releases |
| **Author** | maj0r (project admin), soniciso (account owner) |
| **Description** | All-in-one PS5 utility — save management, cheat integration, FTP services, Linux loading, trophy unlocking, file manager. Successor to Sonic Loader. |
| **License** | GPL-3.0 (glue code); sub-payloads retain their upstream licenses |
| **Firmware** | Unspecified |
| **Hosting** | Gitea (non-GitHub) — requires custom API integration |

### Release Assets (actual tags on Gitea)

| Tag | Date | Asset | Size | Notes |
|-----|------|-------|------|-------|
| v1.6.2 | 2026-05-27 | `elf-arsenal.elf` | 10.4 MB | Latest stable |
| v1.6.1-offlinepack-2026-05-24 | 2026-05-24 | `elf-arsenal.elf` | 8.7 MB | Offline pack build (has elf-arsenal.elf + companion utilities + zip) |
| v1.6.0 | 2026-05-22 | `elf-arsenal.elf` | 8.1 MB | First Elf Arsenal release (rebrand from Sonic Loader) |

**Important:** There is no plain `v1.6.1` tag — only `v1.6.1-offlinepack-2026-05-24` which bundles the elf-arsenal binary alongside companion utilities (cheatrunner.elf) and an offline pack zip. The `gitea-release` fetcher correctly downloads the matching `elf-arsenal.elf` from each release while skipping .zip archives.

### Download Verification

All 3 download URLs confirmed reachable (200 OK):
- ✅ `.../releases/download/v1.6.2/elf-arsenal.elf` → 200, 10.4 MB, ELF magic: 7f454c46
- ✅ `.../releases/download/v1.6.1-offlinepack-2026-05-24/elf-arsenal.elf` → 200, 8.7 MB, ELF magic: 7f454c46
- ✅ `.../releases/download/v1.6.0/elf-arsenal.elf` → 200, 8.1 MB, ELF magic: 7f454c46
- ❌ `.../releases/latest/download/elf-arsenal.elf` → 404 (Gitea doesn't support this pattern)

---

## 3. Implementation: gitea-release sourceType

### 3a. New code in `update_payloads.py`

Two new functions added:

1. **`get_gitea_releases(source_host, repo)`** — Queries `{host}/api/v1/repos/{repo}/releases?limit=N` via HTTP, maps Gitea API response fields (`tag_name`, `published_at`, `prerelease`, `assets`) to internal format matching GitHub's structure.

2. **`update_payload_from_gitea_release(payload_config, metadata)`** — Orchestrates the fetch → asset match → download → hash → metadata pipeline. Normalizes Gitea asset URLs (`browser_download_url` → `url`) for compatibility with `match_asset()` and `download_file()`.

Wired into `main()` via:
```python
elif source_type == 'gitea-release':
    versions = update_payload_from_gitea_release(payload, metadata)
```

### 3b. YAML configuration

```yaml
  - id: elf-arsenal
    displayTitle: Elf Arsenal
    description: All-in-one PS5 homebrew utility — save management, cheats, FTP, Linux loader, trophy unlocker, and file manager. Successor to Sonic Loader. WebUI on port 6969.
    authors:
      - maj0r
      - soniciso
    projectUrl: https://git.etawen.dev/soniciso/elf-arsenal
    sourceType: gitea-release          # NEW source type
    sourceHost: https://git.etawen.dev # NEW field: Gitea instance URL
    sourceRepo: soniciso/elf-arsenal
    sourcePattern: elf-arsenal*.elf
    toPort: 9021
    supportedFirmwares: []
    license:
      type: "GPL-3.0"
      url: "https://git.etawen.dev/soniciso/elf-arsenal"
```

New config fields for `gitea-release`:
- `sourceHost` (required): Base URL of the Gitea instance (e.g., `https://git.etawen.dev`)
- `sourceRepo`: standard `owner/name` format
- `sourcePattern`: asset name glob pattern

### 3c. Sonic Loader deprecation

```yaml
  - id: sonicloader
    willHideEveryTime: true              # NEW: hidden from UI
    description: "[DEPRECATED — superseded by Elf Arsenal] ..."  # UPDATED
    # ... rest unchanged
```

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **sourceType** | `gitea-release` (new) | Dynamic fetching via Gitea REST API — no manual version URLs |
| **sourceHost** | `https://git.etawen.dev` | New config field for non-GitHub instances |
| **Version tracking** | All releases with matching asset | Script fetches all releases, matches `elf-arsenal*.elf`, skips zips |
| **toPort** | `9021` | Same as sonicloader (send through elfldr) |
| **displayTitle** | `Elf Arsenal` | Human-readable with space |
| **authors** | `["maj0r", "soniciso"]` | maj0r is project admin, soniciso is account owner |
| **license** | GPL-3.0 | Explicitly stated in repo |
| **supportedFirmwares** | `[]` (empty) | No single firmware range for the main binary |
| **Placement** | Second (after pldmgr) | User requested |

---

## 4. UI Behavior

- **Post-jailbreak view:** Elf Arsenal appears **second** in the list (after pldmgr). Clicking sends `elf-arsenal.elf` to port 9021 via elfldr.
- **Webkit-only (sender) mode:** Visible — has `toPort: 9021`.
- **Version display:** Shows `1.6.2` (latest) by default. Users can select other versions from Settings.
- **Firmware compatibility:** No badge shown (empty `supportedFirmwares`).
- **Sonic Loader:** Hidden from UI (`willHideEveryTime: true`). Exists on disk for reference.

---

## 5. Automated Updates

The twice-daily GitHub Actions workflow will:
1. Query `https://git.etawen.dev/api/v1/repos/soniciso/elf-arsenal/releases`
2. Find all releases with `elf-arsenal*.elf` assets (skipping .zip archives)
3. Download new binaries, compute SHA256 hashes
4. Preserve existing versions (no data loss on fetch failure)
5. Regenerate `payload_map.js`

**Verified:** git.etawen.dev allows automated HTTP fetches (no anti-bot gate found). All 3 releases downloaded successfully.

---

## 6. Files Changed

| File | Change |
|------|--------|
| `.github/scripts/update_payloads.py` | **Extended** — added `get_gitea_releases()` and `update_payload_from_gitea_release()`, wired into `main()` |
| `.github/payloads.yaml` | Add elf-arsenal entry (second, `gitea-release`), deprecate sonicloader (`willHideEveryTime`, desc) |
| `document/en/ps5/payloads/elf-arsenal/metadata.json` | **Generated** — payload metadata (3 versions) |
| `document/en/ps5/payloads/elf-arsenal/1.6.2/elf-arsenal.elf` | **Downloaded** — 10.4 MB |
| `document/en/ps5/payloads/elf-arsenal/1.6.1-offlinepack-2026-05-24/elf-arsenal.elf` | **Downloaded** — 8.7 MB |
| `document/en/ps5/payloads/elf-arsenal/1.6.0/elf-arsenal.elf` | **Downloaded** — 8.1 MB |
| `document/en/ps5/payloads/sonicloader/metadata.json` | **Updated** — willHideEveryTime, deprecated description |
| `document/en/ps5/payload_map.js` | **Regenerated** — elf-arsenal second, sonicloader hidden |
| `plans/add-elf-arsenal-payload-spec.md` | **Updated** — reflects gitea-release implementation |

---

## 7. Edge Cases & Notes

1. **v1.6.1 tag gap:** No plain `v1.6.1` tag exists — only `v1.6.1-offlinepack-2026-05-24`. The Gitea API correctly returns this tag and `elf-arsenal.elf` is present as an asset.

2. **Companion utilities:** v1.6.1-offlinepack also ships `cheatrunner.elf` and an offline pack ZIP. These are skipped by `match_asset()` (ZIP blocked, cheatrunner doesn't match `elf-arsenal*.elf`).

3. **File naming:** All releases use the same filename (`elf-arsenal.elf`). Version directories disambiguate.

4. **Size:** Total ~27 MB for 3 versions. AppCache only caches the default (v1.6.2, ~10 MB).

5. **Gitea API format differences:** Asset URLs use `browser_download_url` (not `url` like GitHub). Release date is `published_at` (not `publishedAt`). Both are normalized in `get_gitea_releases()`.

6. **No auth needed:** Public Gitea repos don't require API tokens — plain HTTP requests work.
