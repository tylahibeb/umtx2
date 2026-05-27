# Spec: Add pldmgr (PS5 Payload Manager) as a Payload

**Status:** ✅ Implemented — May 27, 2026
**Date:** 2026-05-27
**Request:** Add https://github.com/itsPLK/ps5-payload-manager to the UMTX2 payload list

---

## 1. Summary

Add `pldmgr` (PS5 Payload Manager by itsPLK) as a `github-release` type payload. The repo has proper GitHub Releases with `.elf` assets, so it qualifies for fully automated updates — no manual version management needed.

---

## 2. Source Repository

| Field | Value |
|-------|-------|
| **GitHub URL** | https://github.com/itsPLK/ps5-payload-manager |
| **Author** | itsPLK |
| **Description** | Web-based dashboard to manage, import, and auto-load PS5 payloads. Accessible via PC, phone, or the console itself. Supports USB/cloud import, automated startup, and installs a home-screen shortcut. |
| **License** | Unknown (no LICENSE file found in repo) |
| **Firmware** | Unspecified — depends on the exploit/autoloader in use |

### Release Assets

| Tag | Date | Asset | Pre-release? |
|-----|------|-------|--------------|
| v0.1.1 | 2026-05-02 | `pldmgr-v0.1.1.elf` | No |
| v0.1.0 | 2026-04-30 | `pldmgr_v0.1.0.elf` | No |

**Note:** Asset naming convention is inconsistent — v0.1.0 uses underscore (`_`), v0.1.1 uses hyphen (`-`). The pattern `pldmgr*.elf` matches both.

---

## 3. Payload Configuration

The following entry will be added to `.github/payloads.yaml`:

```yaml
  # --- pldmgr: PS5 Payload Manager (web-based dashboard) ---
  # Repo has GitHub Releases with .elf assets. Asset naming is inconsistent
  # (v0.1.0 uses underscore, v0.1.1+ uses hyphen), so use broad pattern.
  - id: pldmgr
    displayTitle: pldmgr
    description: PS5 payload manager. Runs on PS5 as a web server.
    authors:
      - itsPLK
    projectUrl: https://github.com/itsPLK/ps5-payload-manager
    sourceType: github-release
    sourceRepo: itsPLK/ps5-payload-manager
    sourcePattern: pldmgr*.elf
    toPort: 9021
    supportedFirmwares: []
    license:
      type: ""
      url: ""
```

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **sourceType** | `github-release` | Repo has proper GitHub Releases with `.elf` assets — fully automated |
| **sourcePattern** | `pldmgr*.elf` | Broad pattern catches both naming conventions (underscore + hyphen) |
| **toPort** | `9021` | Sends through elfldr like other network payloads (ftpsrv, websrv, etc.) |
| **displayTitle** | `pldmgr` | Matches the binary naming pattern; short/technical like other PS5 scene tools |
| **license** | Auto-detect → fallback "Unknown" | No LICENSE file in repo; let the script attempt detection, fall back to Unknown |
| **supportedFirmwares** | `[]` (empty) | Project doesn't specify firmware requirements — no restrictions shown in UI |
| **description** | Simple one-liner | Follows existing convention (e.g., "FTP server. Runs on port 2121.") |
| **willHideEveryTime** | Not set (default: false) | Payload is visible to all users |

---

## 4. UI Behavior

- **pldmgr is placed first** in both `payloads.yaml` and `payload_map.js`, making it the first option displayed on the webpage.
- **Post-jailbreak view:** Shows as a regular button. Clicking sends `pldmgr-v{version}.elf` to port 9021 via elfldr.
- **Webkit-only (sender) mode:** Visible — has `toPort: 9021` so it qualifies for sender-only mode.
- **Version display:** Shows `v0.1.1` (latest) by default. Users can select v0.1.0 from Settings.
- **Firmware compatibility:** No badge shown (empty `supportedFirmwares` = universal).
- **Settings view:** Toggleable like all payloads; users can show/hide it.

### UI Naming Consideration

This is a "payload manager" being added to another "payload manager" (UMTX2). However, the display title `pldmgr` is distinct enough from the UMTX2 UI that no special handling or disambiguation is needed.

---

## 5. Automated Updates

The twice-daily GitHub Actions workflow (`static.yml`) will:
1. Poll `itsPLK/ps5-payload-manager` for new releases
2. Match assets against `pldmgr*.elf`
3. Download new versions, calculate SHA256 hashes
4. Parse changelogs from release notes
5. Regenerate `payload_map.js`
6. Auto-commit any changes

No manual intervention required unless the repo is deleted, moved, or switches to ZIP-only releases.

---

## 6. Implementation Steps

### Step 1: Add YAML entry
Add the config block (Section 3) to `.github/payloads.yaml`, placing it alphabetically or in a logical position among the other network payloads.

### Step 2: Run update script locally
```bash
python .github/scripts/update_payloads.py
```
This will:
- Fetch releases from GitHub
- Download `pldmgr-v0.1.1.elf` and `pldmgr_v0.1.0.elf`
- Create `document/en/ps5/payloads/pldmgr/{version}/` directories
- Generate `document/en/ps5/payloads/pldmgr/metadata.json`
- Regenerate `document/en/ps5/payload_map.js`

### Step 3: Run test suite
```bash
python .github/scripts/run_tests.py
```
Validates:
- Payload folder structure exists for `pldmgr`
- `metadata.json` has all required fields
- `payload_map.js` includes the `pldmgr` entry
- All JS files have valid syntax

### Step 4: Regenerate AppCache (optional)
If you want the default pldmgr binary cached for offline use:
```bash
python appcache_manifest_generator.py -d document/en/ps5
```

### Step 5: Commit
```bash
git add .github/payloads.yaml document/en/ps5/payloads/pldmgr/ document/en/ps5/payload_map.js
git commit -m "feat(payloads): add pldmgr (PS5 Payload Manager)"
```

---

## 7. Files Changed

| File | Change |
|------|--------|
| `.github/payloads.yaml` | Add pldmgr config entry |
| `document/en/ps5/payloads/pldmgr/metadata.json` | **Generated** — payload metadata |
| `document/en/ps5/payloads/pldmgr/0.1.1/pldmgr-v0.1.1.elf` | **Downloaded** — latest binary |
| `document/en/ps5/payloads/pldmgr/0.1.0/pldmgr_v0.1.0.elf` | **Downloaded** — previous binary |
| `document/en/ps5/payload_map.js` | **Regenerated** — includes new payload entry |
| `document/en/ps5/cache.appcache` | **Regenerated** (optional) — includes default binary in offline cache |

---

## 8. Edge Cases & Notes

1. **Asset name inconsistency:** If future releases change naming again, the broad `pldmgr*.elf` pattern should still match. If it breaks, tighten to a more specific pattern.

2. **ZIP-only future releases:** If the author switches to ZIP packaging, the script will automatically skip those releases (security policy). A `direct` sourceType with `manualVersions` would then be needed — same treatment as libhijacker and kstuff-toggle.

3. **Repo deletion/move:** If the repo is deleted or moved, the script preserves existing versions from metadata.json to prevent data loss. New versions will stop appearing.

4. **Port conflicts:** If elfldr (port 9021) is not running, sending this payload will fail with a connection error. This is standard behavior for all `toPort: 9021` payloads.

5. **elffldr dependency:** Unlike the README's autoloader recommendation (which is for using pldmgr as a persistent dashboard), sending through UMTX2's elfldr is a one-shot load — the web server will run but won't auto-start on next boot.

---

## 9. Open Questions

- **What port does pldmgr's web server listen on?** Unknown. The project README doesn't specify. Users will discover the port from pldmgr's own output/logging after it starts.
- **Does pldmgr need post-exploit privileges?** It likely needs kernel access (debug menu, root) which UMTX2 provides. If the kernel exploit is skipped (webkit-only mode), it may not function fully.
