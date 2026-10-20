# Optional device offline caching

Offline caching is off by default. In normal Settings, **Save for offline use** saves an explicit per-browser choice. It is no longer a hidden, inverted developer flag.

## Use it

1. Open the site while online and choose Settings → **Save for offline use**.
2. The browser opens the dedicated offline page and downloads the site plus default payload binaries. The Settings control shows the approximate default-payload download size.
3. Wait for **Ready for offline use**, then bookmark the offline page. Open that bookmark without internet. The regular site/root address remains an online entry and cannot start without network.
4. Keep the switch on to receive offline updates when connected. **Check offline files** checks for an update; **Reload updated copy** selects a completed newer cache and reloads.
5. To stop offline downloads and switch back to the online page, turn it off while connected. Switching to the online entry requires internet. Other selected payload versions are not guaranteed offline; only default binaries are included in the manifest.

A default-version badge says **Cached** only when the current page is using offline mode and AppCache has confirmed a complete usable cache. File-download progress reaching 100% is not completion: the browser must commit the cache first. An unsuccessful update can leave an older complete copy available.

Browsers without Application Cache show an unavailable status and disable the switch, while the online host continues working. Modern Chromium is one such browser; the PS5 uses older WebKit. Browser storage failures keep caching off or retain the previous choice and show an error rather than pretending the preference was saved.

## What was broken

- The old root page declared a manifest immediately, before the developer flag could be read. Changing that attribute after parsing cannot opt out of AppCache.
- The label “Disable AppCache” used the opposite checked state and only tried to abort later download events. It did not detach the document or erase stored files.
- The generator restored the root manifest on every deployment.
- Closing Settings prefetched nondefault payloads into ordinary HTTP cache, even when the cache switch was off.
- Default versions were labeled Cached without checking whether a download had completed.
- “Clear All Cache” only cleared local/session preferences. It did not delete browser cache databases.
- Download toasts could intercept the Settings button while a download was active.

## Storage and cleanup

Turning the switch off stops intentional offline downloads and returns to the online page. Existing saved bytes may remain on the device. There is no standard Application Cache API to erase a cache group from JavaScript; `abort()` only stops an update.

To reclaim saved files, use browser website-data controls where available. This repository also has a **Browser appcache remover** custom action, requiring the exploit environment. Its existing implementation deletes AppCache database files for accessible users and can remove offline data for **other hosts too**. It is not invoked automatically by the new switch. That deletion action has not been changed or certified by this work; its UI success messages do not verify every unlink result.

**Reset Settings** resets this host’s payload/developer preferences and pending autorun, preserving the separate offline choice and unrelated website storage. It does not claim to clear cached files.

Ordinary browser HTTP caching is separate from bulk persistent AppCache. Online payload fetches request `cache: 'no-store'`, and opening/closing Settings never prefetches binaries. Browser/server behavior for other normal page assets is outside the offline switch; the switch is not a claim of zero browser storage.

## Entry points and generation

- `document/en/ps5/index.html`: maintained online UI, **no manifest**.
- `document/en/ps5/offline.html`: generated copy with `manifest="offline.appcache"`.
- `document/en/ps5/offline.appcache`: sorted SHA-256 manifest of the offline page, shared assets, metadata, and default payload binaries. It excludes `index.html`, every other HTML entrypoint, manifests, and nondefault binaries. No root aliases or fallback route associates the online entry with the cache.
- `document/en/ps5/js/cache-controller.js`: early head bootstrap. Reads `offline_cache_enabled` (`1`/`0`), defaults off, checks API support, and routes between the entries while preserving query/fragment. The old `dev_mode.disableAppCache` value is not consent. Direct offline URLs cannot override an explicit opt-out. Errors reading storage fail closed.
- The normal Settings controls and toast notifications subscribe to the same lifecycle state. Payload execution and cached badges use the same policy/readiness check.

After editing UI/assets or payload defaults, run:

```sh
python3 appcache_manifest_generator.py -d document/en/ps5
npm test
```

The generator reads defaults from JSON metadata rather than matching JavaScript objects with regex, so braces inside changelogs cannot omit a default payload. It is import-safe and repeatable, uses streaming hashes, and refuses an online source with a manifest attribute. `--clean` removes the generated offline artifacts and legacy manifest without modifying the online source. The old `--update-manifest-tag` and `-cf` switches are accepted for command compatibility but cannot attach/alias the online entry to AppCache.

## Existing-device migration

The legacy `cache.appcache` file is deliberately **deleted**, and generation keeps it absent. Deployments must return a real **404/410** for that URL. Do not restore a 200 response, redirect, or custom static fallback there. The new offline mode uses a different manifest URL to avoid inheriting the automatically cached root.

Removing the root manifest attribute alone does not detach a previously cached master entry. Old clients need an online manifest check to observe the legacy 404, then a reload. Their existing code may display “Site is obsolete” once. Reopen while online and reload; clearing browser AppCache is a fallback if an old client stays stuck. A device that never reconnects cannot receive the migration.

This separation follows older WebKit’s [parser-time manifest selection](https://github.com/qt/qtwebkit/blob/dev/Source/WebCore/html/HTMLHtmlElement.cpp) and [cached-master selection / 404 obsoletion](https://github.com/qt/qtwebkit/blob/dev/Source/WebCore/loader/appcache/ApplicationCacheGroup.cpp). A dynamically added/removed manifest attribute and an iframe-only cache are not substitutes for selecting the cached document itself.

## Validation limits

The regression suite exercises deterministic generation/isolation, actual artifact hashes, opt-in routing, storage failures, AppCache event/readiness behavior, no Settings prefetch, and truthful version badges. Browser checks exercise real Settings/navigation and the unsupported-API path; supported AppCache events are simulated in Chromium because it removed the API. Actual PS5 persistence, storage quotas and offline boot remain device checks.
