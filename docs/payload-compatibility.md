# Payload firmware compatibility audit

Reviewed 2026-10-19. Covers all **40 payload entries** (39 existing plus HearBridge), their checked-in default versions, configured rules, generated metadata and browser filtering. Upstream evidence was checked at the default release/tag where available. This is a documentation/source audit, **not execution on a PS5**.

The host’s kernel exploit supports the 29 firmware points in `document/en/ps5/offsets/`, from 1.00 through 5.50. A payload supporting newer firmware does not extend the host exploit. A firmware rule also cannot certify dependency patches, console model, peripherals, game versions or individual payload features.

## Policy and fixes

- `.github/payloads.yaml` is authoritative. `supportedFirmwares: []` means **no maintained firmware filter**, not verified support everywhere. Missing rules behave the same way. Arbitrary README/topic mentions never become enforced restrictions.
- A trailing-dot rule such as `"4."` matches a major family. A full version such as `"4.03"` or `"7.01.01"` matches exactly. Invalid configured rules fail validation.
- Exact source tables replace broad prefixes where available. This restores supported 1.xx/2.xx entries and excludes documented unsupported firmware points.
- Refresh fingerprints include firmware rules, so compatibility-only updates are detected. AppCache hashes are regenerated; existing PS5 clients must finish updating their cache and reload to use the new map/UI.
- Rules remain **per payload**, audited against the default shown below. Historical selectable versions can have narrower support. This audit does not certify every historical binary against every firmware; version-specific compatibility remains a separate limitation.

## Every payload

“No extra filter” is a display policy. Read the evidence/limits column before treating it as support.

| Payload ID | Audited default | Maintained policy | Evidence and limits |
| --- | --- | --- | --- |
| `kstuff-lite` | 1.2-dr-test2 | 46 exact points (3.00–12.70) | [Source](https://raw.githubusercontent.com/drakmor/kstuff-lite/1.2-dr-test2/prosper0gdb/offsets.c). Source has an explicit 3.00–12.70 offset table. Replaced broad major prefixes with those exact points; 1.xx/2.xx remain excluded. |
| `shadowmountplus` | 1.7-beta5fix1 | No extra filter | [Source](https://raw.githubusercontent.com/drakmor/ShadowMountPlus/1.7-beta5fix1/README.md). Removed the 3/4/5-only cap: the pinned README explicitly includes 2.00. Requires Kstuff-lite v1.07+; the default beta release warns against using etaHEN. This is conditional support, not a standalone firmware guarantee. |
| `etahen` | 2.5B | 52 exact points (1.00–10.60) | [Source](https://raw.githubusercontent.com/etaHEN/etaHEN/2.5B/Source%20Code/bootstrapper/source/main.cpp). Added the documented 1.xx/2.xx support. The pinned bootstrap uses its embedded Byepervisor below 3.00; embedded exploit and libhijacker source tables include the configured points through 10.60; release notes advertise kstuff/cheats only through 10.01. These tables differ from standalone Byepervisor 1.1. |
| `nanodns` | 0.4 | No extra filter | [Source](https://github.com/drakmor/nanoDNS/blob/0.4/README.md). No firmware matrix. Generic SDK consumer; no justified firmware allowlist. |
| `pldmgr` | 0.6.3 | No extra filter | [Source](https://github.com/itsPLK/ps5-payload-manager/blob/v0.6.3/README.md#standalone--manual-loading). No firmware matrix. Current[] should not trigger auto-detection from incidental README mentions. |
| `elf-arsenal` | 1.6.23 | No extra filter | [Source](https://git.etawen.dev/soniciso/elf-arsenal). No maintained filter. Upstream access was denied by this environment’s network policy (proxy CONNECT 403), so a numerical support range could not be verified. Per-feature unsupported-firmware messages in the local binary are not a whole-payload support matrix. |
| `websrv` | 0.35 | No extra filter | [Source](https://github.com/ps5-payload-dev/websrv/blob/v0.35/README.md). No numeric firmware matrix; relies on supported ELF loader/SDK. |
| `ftpsrv` | 0.21.1 | No extra filter | [Source](https://github.com/ps5-payload-dev/ftpsrv/blob/v0.21.1/README.md). Known limitation is SELF reading on some pre-4 firmware, not total payload incompatibility. No justified whole-payload exclusion. |
| `gdbsrv` | 0.9 | No extra filter | [Source](https://github.com/ps5-payload-dev/gdbsrv/blob/v0.9/README.md). No numeric firmware matrix; relies on supported ELF loader/SDK. |
| `klogsrv` | 0.9 | No extra filter | [Source](https://github.com/ps5-payload-dev/klogsrv/blob/v0.9/README.md). No numeric firmware matrix; relies on SDK runtime and privileged /dev/klog access. |
| `shsrv` | 0.20 | No extra filter | [Source](https://github.com/ps5-payload-dev/shsrv/blob/v0.20/README.md). No numeric firmware matrix; relies on supported ELF loader/SDK. |
| `elfldr` | 0.26 | No extra filter | [Source](https://github.com/ps5-payload-dev/elfldr/blob/v0.26/README.md). No numeric firmware matrix; initial injection uses kernel-exploit loader 9020. Do not infer range from dated exploit links. |
| `byepervisor` | 1.1 | 12 exact points (1.00–2.70) | [Source](https://raw.githubusercontent.com/EchoStretch/Byepervisor/1.1/README.md). Retained the exact completed-firmware list from release 1.1. Do not broaden it to every 1.xx/2.xx firmware. |
| `ps5debug-ng` | 1.3.2 | 52 exact points (3.00–13.60) | [Source](https://github.com/OpenSourcereR-dev/ps5debug-NG/blob/1.3.2/README.md#supported-firmwares). Added the explicit firmware allowlist from the pinned 1.3.2 README and installer switch. The installer aborts outside recognized points; 1.xx/2.xx are not supported. |
| `ps5upload` | 7.1.9 | No extra filter | [Source](https://github.com/phantomptr/ps5upload/blob/v7.1.9/README.md#supported-platforms). Removed the fabricated 5/3 restriction. The pinned 7.1.9 README explicitly supports 1.00–13.60, including 4.xx; tested upstream on 5.10, 9.60 and 13.60. Requires the ELF loader on port 9021. |
| `hearbridge` | 1.3.6 | No extra filter | [Source](https://github.com/X-F1REBALL-X/HearBridge-PS5/blob/v1.3.6/README.md). Added stable 1.3.6 with no maintained numerical filter. Upstream describes a unified firmware build and console Bluetooth support. Needs an ELF loader and A2DP/SBC headphones or speaker; no microphone. Hardware behavior on this host’s firmware was not tested. Stable releases only; exclude firmware-specific and MediaTek test assets. |
| `ps5-game-compressor` | 1.0.4 | No extra filter | [Source](https://github.com/juma-sayeh/PS5-Game-Compressor/blob/v1.0.4/README.md#requirements). No firmware matrix. Actual capability depends on SMP and KStuff Lite, cannot label [] as guaranteed all-firmware support. |
| `cheatrunner` | 0.18 | No extra filter | [Source](https://github.com/notmaj0r/CheatRunner/blob/v0.18/README.md#requirements). No numeric firmware matrix; leave [] as no extra filter, not verified compatibility. |
| `ps5debug-dizz` | 0.0.1-r2 | No extra filter | [Source](https://github.com/idlesauce/ps5debug/blob/v0.0.1-r2/readme.md). Upstream readme is lowercase readme.md. No firmware matrix; preserve [] without claiming universal verification. README explicitly unfinished debugger. |
| `ps5-versions` | 1.0 | No extra filter | [Source](https://raw.githubusercontent.com/SiSTR0/ps5-versions/v1.0/source/main.c). Removed the unsupported 1–4-only cap. Pinned source uses loader-provided dlsym/sysctl rather than firmware-specific offsets. No numerical support matrix or hardware verification for other versions was found. |
| `rp-get-pin` | 0.1.1 | No extra filter | [Source](https://github.com/idlesauce/ps5-remoteplay-get-pin/blob/v0.1.1/README.md). No numeric firmware matrix. Offline activated account required; some users need reboot. No justified narrowing. |
| `backpork` | 0.1 | No extra filter | [Source](https://raw.githubusercontent.com/BestPig/BackPork/0.1/README.md). No maintained firmware filter. Upstream documents library patches working on 7.61 and says lower firmware needs additional untested patches. A successful payload load would not establish game/library backport compatibility on this host. |
| `kstuff-lite-echostretch` | 1.11 | 67 exact points (1.00–13.60) | [Source](https://github.com/EchoStretch/kstuff-lite/releases/tag/v1.11). Added the omitted 1.xx/2.xx and 13.xx points. Release 1.11 and its source cover the exact configured 1.00–13.60 firmware table. |
| `kstuff-lite-1200-only` | 1.1-dr | `12.00` | [Source](https://github.com/drakmor/kstuff-lite/releases/tag/1.1-dr). Restricted this special local asset to exactly 12.00, rather than all 12.xx. Still forced hidden; it is not the generic drakmor release binary. |
| `kylin-core` | 2.0.0-community-lite | 45 exact points (4.03–13.60) | [Source](https://raw.githubusercontent.com/aydencharles/kylin-core-release/v2.0.0-community-lite/README.md). Corrected the lower bound to 4.03 and included the documented upper range through 13.60 using known firmware points. The pinned README writes the minimum as 4.0.3. 4.00/4.02 are excluded. |
| `bfpilot` | 0.4.4 | No extra filter | [Source](https://github.com/ItsBlurf/BFpilot/blob/v0.4.4/README.md). Removed the fabricated 4-only restriction. The pinned compatibility strategy says there are no firmware-specific offsets; older/newer firmware use different installer identities. Upstream reports testing only on 11.60, so host firmware behavior is unverified. |
| `webkit-cache-remover` | 1.02 | No extra filter | [Source](https://github.com/vladimir-cucu/ps5-webkit-cache-remover/blob/v1.02/README.md). Tested 4.51 is not an exclusive allowlist. No justified firmware narrowing. Other host firmware points unverified. |
| `kstuff-echostretch` | 1.6.7 | 33 exact points (3.00–10.01) | [Source](https://github.com/EchoStretch/kstuff/releases/tag/v1.6.7). Release 1.6.7 advertises 3.00–10.01. Rules now list the known firmware points within that range; no 1.xx/2.xx support inferred. |
| `kstuff` | 1.5 | `3.`, `4.`, `5.` | [Source](https://github.com/EchoStretch/ps4jb-payloads/releases/tag/kstuff-ps5). Original configured repository/release returned 404. Retained the existing 3/4/5 policy for this legacy 1.5 binary; compatibility remains unverified. Newer similarly named projects do not certify it. |
| `kstuff-toggle` | 0.2 | 22 exact points (3.00–7.61) | [Source](https://raw.githubusercontent.com/EchoStretch/kstuff-toggle/0.2/main.c). Pinned 0.2 source has an explicit 3.00–7.61 firmware switch; use its exact table. Requires kstuff already running. Cases for 1.xx/2.xx do not toggle. |
| `kstuff-toggle-ps5` | 0.6 | 47 exact points (3.00–13.20) | [Source](https://raw.githubusercontent.com/EchoStretch/kstuff-toggle/0.6/main.c). Pinned 0.6 source supplies an exact table through 13.20; requires running kstuff. The locally supplied PS5 variant is not independently attested as built from that source. |
| `kstuff-toggle-ps4` | 0.6 | 47 exact points (3.00–13.20) | [Source](https://raw.githubusercontent.com/EchoStretch/kstuff-toggle/0.6/main.c). Pinned 0.6 source supplies an exact table through 13.20; requires running kstuff. This means the PS4 game patches on a PS5, not a PS4-console binary. Local variant/source identity is unverified. |
| `kstuff-toggle-both` | 0.6 | 47 exact points (3.00–13.20) | [Source](https://raw.githubusercontent.com/EchoStretch/kstuff-toggle/0.6/main.c). Pinned 0.6 source supplies an exact table through 13.20; requires running kstuff. Local combined variant/source identity is unverified. |
| `libhijacker` | 1.160 | `3.`, `4.` | [Source](https://github.com/illusion0001/libhijacker-game-patch). Original repository and documented mirror README requests returned 404. Retained the 3/4 policy for local 1.160; compatibility unverified. Do not infer support from current forks. |
| `ps5debug` | 1.0b5 | `3.`, `4.`, `5.` | [Source](https://github.com/GoldHEN/ps5debug). Original GoldHEN repository returned 404. Retained the 3/4/5 rule for local 1.0b5, with compatibility unverified; maintained forks are separate payloads. |
| `ps5-hen` | dev-latest | 25 exact points (1.00–4.51) | [Source](https://raw.githubusercontent.com/cragson/ps5-hen/ab93d63e816d1a1aeeef349726630ba377c71843/README.md). Pinned development commit documents exact firmware through 4.51. Replaced broad 1/2/3/4 prefixes with that list; 5.xx remains excluded. |
| `sonicloader` | 1.6.0-elf-arsenal-rebrand | No extra filter | [Source](https://git.earthonion.com/soniciso/sonicloader). Deprecated and forced hidden. Upstream access was denied by network policy (proxy CONNECT 403). Local default bytes match Elf Arsenal 1.6.0 exactly; that relationship does not establish firmware compatibility. |
| `appcache-remove` | 1.0 | No extra filter | [Source](../document/en/ps5/main.js). JavaScript action implemented by this host, with no downloaded binary. Follows the host exploit/ROP/syscall availability; WebKit-only mode has user-access limits. Deletion behavior was not tested on hardware. |
| `umtx2-host` | 1.0 | No extra filter | [Source](../document/en/ps5/payloads/umtx2-host/metadata.json). Local custom ELF with no upstream source/build provenance or support table configured. Retained no filter; compatibility is unverified. Binary contains this fork’s Pages URL. |
| `phu-overlay` | 1.15.0-alpha | 46 exact points (3.00–12.70) | [Source](../.github/payloads.yaml). Added exact 3.00–12.70 points matching the configured description and firmware table strings in the local ELF, excluding 1.xx/2.xx. Requires kstuff. Evidence is provisional: no upstream source/provenance URL is supplied, and strings do not prove runtime support. |

## Important uncertainty

- Legacy `kstuff`, `libhijacker`, and GoldHEN `ps5debug` sources are unavailable. Their existing rules are retained rather than replaced with claims from other binaries/forks.
- Elf Arsenal and Sonic Loader upstreams were blocked by this environment’s network policy. This does not establish that those projects are unavailable publicly.
- `umtx2-host` and PHU are locally supplied binaries without an upstream source/provenance URL. PHU’s description and binary table corroborate its lower bound, but do not replace source or hardware validation.
- Most SDK utilities publish no numerical firmware matrix. Their no-filter policy is retained with that uncertainty documented. WebKit Cache Remover is explicitly tested upstream only on 4.51; BFpilot only on 11.60. Those tests do not establish exclusive allowlists.
- BackPork’s library backport patches and FTP’s documented pre-4 SELF-read stalls are feature limitations, not evidence that a successful payload launch guarantees its intended operation.

## HearBridge release selection

The added `hearbridge` entry automatically tracks stable GitHub releases. `includePrereleases: false` prevents 1.3.7-beta.1 from replacing stable 1.3.6. `sourceExcludePatterns` skips historical `*-fw*.elf` and `*-mtk-test.elf` variants before asset selection and while preserving existing versions. These globs apply to release asset names, not archive members.

Eight normal stable releases were imported, 1.0.0 through 1.3.6. Each downloaded ELF matched GitHub’s published SHA-256 digest. Default 1.3.6 is 744,056 bytes, SHA-256 `7b1a1b4a9a44db0723692a83718ebca63ecef38875a53a41328950f2cfa6877c`. Control UI port 8090 is separate from payload injection port 9021. Its built-in Bluetooth bridge supports SBC audio; it does not require a USB Bluetooth dongle.

## Maintaining the rules

1. Check the actual default release’s documentation/source. Update the YAML and this report with evidence and dependencies; avoid converting a single tested version into an exclusive allowlist.
2. With PyYAML and requests installed, refresh existing local metadata and generated maps without downloading releases:
   ```sh
   python3 .github/scripts/update_payloads.py --compatibility-only
   ```
   This preserves binary versions/hashes and refuses missing metadata or orphaned payload directories. For a new payload, import its binaries/metadata through the regular release updater first.
3. Regenerate the offline cache and run all checks:
   ```sh
   python3 appcache_manifest_generator.py -d document/en/ps5
   npm test
   ```
4. Publish the updated site through the repository’s normal deployment process. Existing clients must let AppCache update and then reload. Refresh only checks for changes; it does not replace the running map or clear AppCache.

The automated firmware regressions exercise the real generator/filter/fingerprint code, all 40 map/metadata rules, exact and major matching, stable-release and asset policies, and offline rebuilding. No existing binary or version was changed during the audit.
