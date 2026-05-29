# Spec: Add kstuff-lite (EchoStretch) as a new payload

**Status:** 📋 Draft — pending implementation
**Date:** 2026-05-29
**Request:** Add https://github.com/EchoStretch/kstuff-lite/releases to the list of payloads

---

## 1. Summary

Add **kstuff-lite by EchoStretch** (`EchoStretch/kstuff-lite`) as a `github-release` sourceType payload. This is EchoStretch's **official upstream version** of kstuff-lite — distinct from the existing:
- `kstuff-lite` (drakmor's performance-optimized fork, from `drakmor/kstuff-lite`)
- `kstuff-echostretch` (EchoStretch's community fork of the original kstuff, from `EchoStretch/kstuff`)

No new code is needed — this is a standard `github-release` sourceType, fully supported by the existing auto-update pipeline.

---

## 2. Source Repository

| Field | Value |
|-------|-------|
| **URL** | https://github.com/EchoStretch/kstuff-lite |
| **Releases API** | Standard GitHub Releases API (via `gh` CLI) |
| **Author** | EchoStretch |
| **Description** | FPKG enabler — EchoStretch's official upstream kstuff-lite |
| **License** | Auto-detect from GitHub API |
| **Firmware** | 3.00–12.70 (varies by release; broadest range used in config) |
| **Hosting** | GitHub (standard) |

### Release Assets (verified via browser — 2026-05-29)

| Tag | Date | Binary Asset | Source Archives | Notes |
|-----|------|-------------|-----------------|-------|
| v1.06 | 2026-05-25 | `kstuff.elf` ✅ | zip, tar.gz | Beta — Supports FW 3.00–12.70 |
| v1.05 | 2026-05-22 | ❌ None | zip, tar.gz | Source code only — no binary |
| v1.04 | 2026-05-02 | ❌ None | zip, tar.gz | Source code only — no binary |
| v1.03 | 2026-04-04 | ❌ None | zip, tar.gz | Source code only — no binary |
| v1.02 | 2026-04-03 | ❌ None | zip, tar.gz | Source code only — no binary |
| v1.01 | 2026-03-29 | ❌ None | zip, tar.gz | Source code only — no binary |
| v1.00 | 2026-02-03 | ❌ None | zip, tar.gz | Source code only — no binary |

**⚠️ Critical finding:** Only v1.06 has a downloadable binary asset (`kstuff.elf`). All previous releases (v1.00–v1.05) only contain source code archives (`.zip` and `.tar.gz`), which the auto-updater **explicitly skips** per security policy. This means:
- With `github-release` sourceType, only v1.06 will be fetched
- v1.06 is a Beta/pre-release, so it will be the only version available
- Since it's the only version, it will also be the default (`isDefault: true`)

**Asset filename:** `kstuff.elf` (confirmed for v1.06)
**Asset pattern:** `kstuff*.elf`
**v1.06:** Tagged as Beta → will be marked `isPreRelease: true`, but since it's the only version with a binary, it will still be the default

---

## 3. YAML Configuration

```yaml
  # --- kstuff-lite (EchoStretch): Official upstream FPKG enabler ---
  # EchoStretch's own kstuff-lite repo — distinct from drakmor's fork
  # and EchoStretch/kstuff (the original community fork).
  # Only v1.06 has a downloadable kstuff.elf binary; older releases are source-code-only.
  - id: kstuff-lite-echostretch
    displayTitle: kstuff-lite (EchoStretch)
    description: FPKG enabler — EchoStretch's official upstream kstuff-lite
    authors:
      - EchoStretch
    projectUrl: https://github.com/EchoStretch/kstuff-lite
    sourceType: github-release
    sourceRepo: EchoStretch/kstuff-lite
    sourcePattern: kstuff*.elf
    toPort: 9021
    supportedFirmwares:
      - "3."
      - "4."
      - "5."
      - "6."
      - "7."
      - "8."
      - "9."
      - "10."
      - "11."
      - "12."
    license:
      type: ""
      url: ""
```

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Payload ID** | `kstuff-lite-echostretch` | User chose — consistent with `kstuff-echostretch` naming convention |
| **Display Title** | `kstuff-lite (EchoStretch)` | User chose — mirrors `kstuff-lite (drakmor fork)` convention |
| **sourceType** | `github-release` | Standard GitHub releases — fully automated, no code changes needed |
| **sourcePattern** | `kstuff*.elf` | Asset confirmed as `kstuff.elf` across all releases |
| **Authors** | `["EchoStretch"]` | Primary maintainer of the repo |
| **License** | Auto-detect (empty) | Let `detect_license()` query GitHub API |
| **supportedFirmwares** | All major families 3.x–12.x | User chose broad range to capture all release FW support |
| **toPort** | `9021` | Standard for elfldr-sent payloads |
| **Visibility** | Fully visible (`visible: true`) | No `willHideEveryTime` — user wants it shown |
| **v1.06 (Beta)** | Marked as pre-release | User confirmed — `isPrerelease: true`, but since it's the only version with a binary, it will also be the default |

---

## 4. UI Behavior

- **Post-jailbreak view:** Appears in the main payload list alongside the other kstuff variants.
- **Webkit-only (sender) mode:** Visible — has `toPort: 9021`.
- **Version display:** Shows `1.06` (Beta) as the only available version.
- **Firmware compatibility:** Badge shows broad FW support (3.x–12.x).

### Relationship to existing kstuff payloads

| ID | Display Title | Repo | Role |
|----|--------------|------|------|
| `kstuff` | ps5-kstuff | EchoStretch/ps4jb-payloads | Original distribution (direct, single version) |
| `kstuff-echostretch` | ps5-kstuff (EchoStretch fork) | EchoStretch/kstuff | Community fork with extra patches |
| `kstuff-lite` | kstuff-lite (drakmor fork) | drakmor/kstuff-lite | Performance-optimized fork |
| **`kstuff-lite-echostretch`** | **kstuff-lite (EchoStretch)** | **EchoStretch/kstuff-lite** | **Official upstream (NEW)** |
| `kstuff-lite-1200-only` | kstuff-lite (FW 12.00 only) | drakmor/kstuff-lite | FW 12.00 specific (hidden) |

---

## 5. Automated Updates

The twice-daily GitHub Actions workflow will:
1. Run `gh release list --repo EchoStretch/kstuff-lite` to get all releases
2. For each release, run `gh release view TAG` to get assets, body, publishedAt
3. Match assets against `kstuff*.elf` pattern → find `kstuff.elf`
4. Download new binaries, compute SHA256 hashes, parse changelogs
5. Preserve existing versions on disk (no data loss on fetch failure)
6. Mark v1.06 as `isPreRelease: true` (Beta)
7. Regenerate `payload_map.js` and `metadata.json`

**Expected:** Only 1 version (v1.06) will be discovered and downloaded. The other 6 releases have no matching binary assets and will be preserved from existing metadata only if already on disk (they aren't — this is a new payload).

---

## 6. Files Changed

| File | Change |
|------|--------|
| `.github/payloads.yaml` | Add `kstuff-lite-echostretch` entry |
| `document/en/ps5/payloads/kstuff-lite-echostretch/metadata.json` | **Generated** — payload metadata (1 version: v1.06) |
| `document/en/ps5/payloads/kstuff-lite-echostretch/1.06/kstuff.elf` | **Downloaded** — ~1.5 MB |
| `document/en/ps5/payload_map.js` | **Regenerated** — new payload included |

---

## 7. Edge Cases & Notes

1. **Asset name collision:** All releases use the same filename `kstuff.elf`. The version directory (`{version}/kstuff.elf`) disambiguates.

2. **v1.06 Beta handling:** Since v1.06 is tagged as Beta and is the **only** version with a binary asset, it will be marked `isPreRelease: true` but will still be the default (`isDefault: true`) — there's no alternative. When EchoStretch publishes a stable v1.07 (or newer) with `.elf` assets, the auto-updater will make that the new default.

3. **Similar naming:** The `sourcePattern: kstuff*.elf` is the same pattern used by `kstuff-echostretch` and `kstuff-lite`. This is fine — each repo only has its own `kstuff.elf` asset.

4. **Size estimation:** Only v1.06 has a binary — ~1.5 MB total. AppCache caches the default version (~1.5 MB).

**⚠️ Single-version payload:** Since only v1.06 provides a downloadable binary, this payload will have exactly 1 version at launch. If EchoStretch publishes future releases with `.elf` assets, the auto-updater will pick them up. If they continue the source-code-only pattern for future releases, this payload will stay pinned to v1.06.

5. **No new code needed:** This is a standard `github-release` sourceType — the existing `update_payload_from_github_release()` function handles it without modification.

6. **FW range vs per-version FW:** `supportedFirmwares` uses the broadest range (3.x–12.x). Individual releases may support narrower ranges (e.g., v1.00 only goes up to 10.01), but the UI-level FW badge shows the broad union. Users should consult individual release notes for exact FW compatibility.
