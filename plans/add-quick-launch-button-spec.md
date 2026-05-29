# Spec: Add Quick Launch Multi-Payload Button

**Status:** 📋 Draft — pending implementation
**Date:** 2026-05-29
**Request:** Add a full-width button to the top of the payload selections that launches kstuff-lite (drakmor), shadowmountplus, and etahen in order with a delay between each.

---

## 1. Summary

Add a **"Quick Launch"** button to the `payloads-view` that dispatches the three priority payloads sequentially:
1. **kstuff-lite (drakmor fork)** — FPKG enabler
2. **ShadowMountPlus** — Game image mounter
3. **etaHEN** — AIO HEN

The button uses the **default version** of each payload (ignoring user-selected versions from Settings), dispatches them with a **3-second gap** between each, shows a **combined progress toast**, and **stops on first failure**. It's placed in its own row **between the top bar and the payload grid**, styled with a **distinct accent** to stand out.

---

## 2. Design Decisions (from user interview)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Button label** | "Quick Launch" | Simple, efficient — doesn't name specific payloads |
| **Button style** | Distinct accent | Stands out from regular payload buttons — gradient/icon/special color |
| **Placement** | Between grid and top bar | Its own row, most prominent position, doesn't interfere with grid layout |
| **Delay timing** | Between dispatches | Fire-and-forget loop with 3s gap. Main loop processes them sequentially anyway |
| **Exact delay** | 3 seconds | Minimum of 3-5s range — fastest while giving elfldr breathing room |
| **Version selection** | Always default/latest | Uses `isDefault: true` version, ignores user's Settings version |
| **Error handling** | Stop on first failure | Prevents partial state (e.g., kstuff without etaHEN) |
| **Progress feedback** | Combined progress toast | Single persistent toast: "Quick Launch (1/3)" → "(2/3)" → "(3/3)" → "Done ✅" |
| **Webkit-only mode** | Show the button | All 3 payloads send to port 9021 via elfldr, works in sender mode |
| **Visibility settings** | Launch regardless | Bypasses Settings visibility toggles — Quick Launch always sends all 3 |

---

## 3. Button Behavior

### 3.1 Trigger Flow

```
User clicks "Quick Launch"
    ↓
Show combined toast: "Quick Launch: Starting..."
    ↓
Dispatch kstuff-lite (default version) → CustomEvent(MAINLOOP_EXECUTE_PAYLOAD_REQUEST)
    ↓
Toast updates: "Quick Launch: kstuff-lite (1/3)"
    ↓
Wait 3 seconds (setTimeout)
    ↓
Dispatch ShadowMountPlus (default version)
    ↓
Toast updates: "Quick Launch: ShadowMountPlus (2/3)"
    ↓
Wait 3 seconds (setTimeout)
    ↓
Dispatch etaHEN (default version)
    ↓
Toast updates: "Quick Launch: etaHEN (3/3) — Done ✅"
    ↓
Toast auto-dismisses after TOAST_SUCCESS_TIMEOUT (2s)
```

### 3.2 Error Handling

If **any** payload fails during execution:
- The queue (in `main.js`) catches the error and shows a per-payload error toast
- The Quick Launch aborts the remaining dispatches
- The combined progress toast updates to: "Quick Launch: Failed ❌" and dismisses after `TOAST_ERROR_TIMEOUT` (5s)

### 3.3 Payload Resolution

Each payload is resolved using `resolveActiveVersion()` but **overriding to always use the default**. Specifically:
- Look up the payload in `payload_map` by ID
- Find the version with `isDefault: true` (or versions[0] as fallback)
- Use `version.filePath` for the fetch path
- Set `toPort` to `9021` (all three already have this)

### 3.4 Respect for Existing Queue

The Quick Launch dispatches each payload by firing a `CustomEvent(MAINLOOP_EXECUTE_PAYLOAD_REQUEST)`. The existing queue in `main.js` processes them. If another payload was already queued by the user, the Quick Launch payloads join the queue and process in FIFO order after the existing items.

---

## 4. UI Design

### 4.1 Placement

```
┌─────────────────────────────────────────────┐
│  PS5 UMTX2 Jailbreak (1.xx-5.xx)            │  ← top-bar-row
│  Listening on: 192.168.1.5 (port 9020, 9021)│
├─────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────┐│
│  │  ⚡ Quick Launch                         ││  ← NEW: full-width accent button
│  │  kstuff-lite + ShadowMountPlus + etaHEN  ││     (between top bar and grid)
│  └─────────────────────────────────────────┘│
├─────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────────────┐ │
│  │ kstuff-lite  │  │ ShadowMountPlus      │ │  ← payload grid (2 columns)
│  │ (drakmor)    │  │                      │ │
│  └──────────────┘  └──────────────────────┘ │
│  ┌──────────────┐  ┌──────────────────────┐ │
│  │ etaHEN       │  │ pldmgr               │ │
│  └──────────────┘  └──────────────────────┘ │
│  ...                                         │
└─────────────────────────────────────────────┘
```

### 4.2 Styling

The button is **not** a regular `.btn` — it gets its own CSS class:

```css
.quick-launch-btn {
    width: 100%;
    padding: 1rem 2rem;
    border-radius: 1.25rem;
    border: none;
    cursor: pointer;
    font-size: 1.3rem;
    font-weight: bold;
    
    /* Distinct accent - gradient background */
    background: linear-gradient(135deg, #1a73e8, #7c4dff);
    color: #ffffff;
    
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    
    transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.25s ease;
    box-shadow: 0 2px 8px rgba(124, 77, 255, 0.3);
}

.quick-launch-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(124, 77, 255, 0.5);
}

.quick-launch-btn:active {
    transform: translateY(0);
    box-shadow: 0 1px 4px rgba(124, 77, 255, 0.3);
}
```

### 4.3 Subtitle

Below the main label, a smaller subtitle lists the payloads:
- Format: `kstuff-lite + ShadowMountPlus + etaHEN`
- Font size: ~0.85rem
- Opacity: 0.8

### 4.4 Icon

A lightning bolt ⚡ or similar icon on the left side of the button label, using SVG or emoji.

---

## 5. Toast Behavior

### 5.1 Combined Progress Toast

A **single** persistent toast element is created when Quick Launch starts. It updates in place with progress:

| Stage | Toast Message | Duration |
|-------|--------------|----------|
| Start | "Quick Launch: Starting..." | ~0ms (immediately updates) |
| After dispatch 1 | "Quick Launch: kstuff-lite (1/3)" | 3s until next dispatch |
| After dispatch 2 | "Quick Launch: ShadowMountPlus (2/3)" | 3s until next dispatch |
| After dispatch 3 | "Quick Launch: etaHEN (3/3) — Done ✅" | TOAST_SUCCESS_TIMEOUT (2s) |
| On error | "Quick Launch: Failed ❌ — [payload] error" | TOAST_ERROR_TIMEOUT (5s) |

The combined toast uses `updateToastMessage()` for in-place updates (avoiding toast spam). Individual payload execution will also create their own toasts from the queue processor — those should be suppressed or the combined toast should be the only one.

**Decision:** Suppress individual payload toasts during Quick Launch. Only the combined progress toast is shown. This avoids "toast noise" of seeing up to 4 toasts simultaneously.

### 5.2 Implementation Approach

The combined toast is managed entirely by the Quick Launch button handler. Since the queue in `main.js` creates toasts for each queued payload automatically, we need a way to suppress those during a Quick Launch sequence. Options:

**Option A (recommended): Global flag** — Set a `window.quickLaunchInProgress = true` flag. The queue processor in `main.js` checks this flag and skips its normal `showToast()` call for individual payloads when it's set.

**Option B: Replace toast function** — Temporarily swap `showToast` with a no-op during the sequence.

**Option C: Use toast container as-is** — Let individual toasts show alongside the combined one. Simple but noisy.

**Recommendation:** Option A — minimal code change, clean separation.

---

## 6. Files to Change

| File | Change | Complexity |
|------|--------|------------|
| `document/en/ps5/js/ui/payloads-view.js` | Add Quick Launch button to `populatePayloadsPage()`, dispatch logic, toast management | Medium |
| `document/en/ps5/main.css` | Add `.quick-launch-btn`, `.quick-launch-subtitle`, `.quick-launch-container` styles | Small |
| `document/en/ps5/main.js` | Add `window.quickLaunchInProgress` flag check in queue processor to suppress toasts | Tiny |

---

## 7. Implementation Details

### 7.1 `payloads-view.js` Changes

After clearing `payloadsView` children and before the `for` loop, insert:

```javascript
// Quick Launch button
var quickLaunchContainer = document.createElement("div");
quickLaunchContainer.className = "quick-launch-container";

var quickLaunchBtn = document.createElement("button");
quickLaunchBtn.className = "quick-launch-btn";
quickLaunchBtn.innerHTML = '<span class="quick-launch-icon">⚡</span><span>Quick Launch</span>';

var quickLaunchSubtitle = document.createElement("p");
quickLaunchSubtitle.className = "quick-launch-subtitle";
quickLaunchSubtitle.textContent = "kstuff-lite + ShadowMountPlus + etaHEN";

quickLaunchBtn.appendChild(quickLaunchSubtitle);
quickLaunchContainer.appendChild(quickLaunchBtn);
payloadsView.appendChild(quickLaunchContainer);

quickLaunchBtn.addEventListener("click", function() {
    startQuickLaunch();
});
```

Define `startQuickLaunch()`:

```javascript
var QUICK_LAUNCH_PAYLOADS = ["kstuff-lite", "shadowmountplus", "etahen"];
var QUICK_LAUNCH_DELAY_MS = 3000;

function startQuickLaunch() {
    var toast = showToast("Quick Launch: Starting...", -1);
    window.quickLaunchInProgress = true;
    
    var dispatched = 0;
    var failed = false;
    
    function dispatchNext() {
        if (failed || dispatched >= QUICK_LAUNCH_PAYLOADS.length) {
            return;
        }
        
        var payloadId = QUICK_LAUNCH_PAYLOADS[dispatched];
        var payload = payload_map.find(function(p) { return p.id === payloadId; });
        
        if (!payload) {
            updateToastMessage(toast, "Quick Launch: Failed ❌ — payload '" + payloadId + "' not found");
            setTimeout(function() { removeToast(toast); }, TOAST_ERROR_TIMEOUT);
            window.quickLaunchInProgress = false;
            return;
        }
        
        // Resolve default version (always use default, ignoring user selection)
        var defaultVer = payload.versions.find(function(v) { return v.isDefault; }) || payload.versions[0];
        var filePath = defaultVer.filePath || ("payloads/" + defaultVer.fileName);
        
        var resolvedPayload = {};
        for (var key in payload) { resolvedPayload[key] = payload[key]; }
        resolvedPayload.version = defaultVer.version;
        resolvedPayload.fileName = defaultVer.fileName;
        resolvedPayload.filePath = filePath;
        
        updateToastMessage(toast, "Quick Launch: " + payload.displayTitle + " (" + (dispatched + 1) + "/" + QUICK_LAUNCH_PAYLOADS.length + ")");
        
        window.dispatchEvent(new CustomEvent(MAINLOOP_EXECUTE_PAYLOAD_REQUEST, { detail: resolvedPayload }));
        
        dispatched++;
        
        if (dispatched >= QUICK_LAUNCH_PAYLOADS.length) {
            // All dispatched — the main loop will process them
            // We mark progress as done; the main loop handles errors
            updateToastMessage(toast, "Quick Launch: All dispatched ✅ (" + QUICK_LAUNCH_PAYLOADS.length + "/" + QUICK_LAUNCH_PAYLOADS.length + ")");
            setTimeout(function() {
                removeToast(toast);
                window.quickLaunchInProgress = false;
            }, TOAST_SUCCESS_TIMEOUT);
        } else {
            setTimeout(dispatchNext, QUICK_LAUNCH_DELAY_MS);
        }
    }
    
    dispatchNext();
}
```

### 7.2 `main.js` Changes

In the queue processing loop, wrap the toast creation:

```javascript
// Current code:
let toast = showToast(`${payload_info.displayTitle}: Waiting in queue...`, -1);

// Change to:
if (!window.quickLaunchInProgress) {
    let toast = showToast(`${payload_info.displayTitle}: Waiting in queue...`, -1);
    queue.push({ payload_info, toast });
} else {
    queue.push({ payload_info, toast: null });
}
```

And where toasts are referenced:

```javascript
// Before:
updateToastMessage(toast, `${payload_info.displayTitle}: Fetching...`);
// After:
if (toast) updateToastMessage(toast, `${payload_info.displayTitle}: Fetching...`);
// ... repeat for all updateToastMessage and setTimeout(removeToast, ...) calls
```

### 7.3 `main.css` Changes

```css
/* Quick Launch button container */
.quick-launch-container {
    grid-column: 1 / -1;
    padding: 0.5rem 0;
}

.quick-launch-btn {
    width: 100%;
    padding: 1rem 2rem;
    border-radius: 1.25rem;
    border: none;
    cursor: pointer;
    font-size: 1.3rem;
    font-weight: bold;
    
    background: linear-gradient(135deg, #1a73e8, #7c4dff);
    color: #ffffff;
    
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.25rem;
    
    transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.25s ease;
    box-shadow: 0 2px 8px rgba(124, 77, 255, 0.3);
    
    position: relative;
}

.quick-launch-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(124, 77, 255, 0.5);
}

.quick-launch-btn:active {
    transform: translateY(0);
    box-shadow: 0 1px 4px rgba(124, 77, 255, 0.3);
}

.quick-launch-icon {
    font-size: 1.5rem;
}

.quick-launch-subtitle {
    color: rgba(255, 255, 255, 0.8);
    margin: 0;
    padding: 0;
    font-size: 0.85rem;
    font-weight: 400;
}
```

---

## 8. Edge Cases & Notes

1. **Webkit-only mode:** The button still appears. All three payloads have `toPort: 9021` and work in sender-only mode.

2. **Queue interference:** If the user manually queues a payload before clicking Quick Launch, that payload runs first. The Quick Launch payloads join after it. Combined toast timing stays accurate since it counts dispatches, not completions.

3. **Double-click prevention:** The button should be disabled after first click to prevent duplicate dispatches. Re-enable after the sequence completes or fails.

4. **Missing payloads:** If any of the 3 payload IDs aren't found in `payload_map`, show an error and stop. This shouldn't happen but is a safety check.

5. **Firmware compatibility:** Since we're bypassing visibility settings, we also bypass firmware compatibility checks for the Quick Launch button. However, the individual payload dispatch through the main loop still respects firmware compatibility (the payload wouldn't be in the grid anyway — it's filtered out by `populatePayloadsPage()`).

6. **Pre-release versions:** If the default version is a pre-release, we still use it. The user explicitly chose "use default/latest."

7. **No Settings impact:** Quick Launch doesn't read or write Settings. It doesn't change user-selected versions. It's a one-shot "just send the defaults" action.

8. **CSS Grid integration:** The button sits in its own container div that uses `grid-column: 1 / -1` to span both columns of the 2-column payload grid. It's inserted before the grid items, placing it above them.

9. **Main loop toast suppression:** The `quickLaunchInProgress` flag approach is simpler than replacing functions. The flag must be cleared after the sequence finishes OR on error to prevent permanent toast suppression.

---

## 9. Testing Plan

1. **Basic flow:** Click Quick Launch → verify 3 payloads dispatched with 3s gaps → verify combined toast updates → verify payloads execute
2. **Error handling:** Simulate a payload failure → verify remaining dispatches are cancelled → verify error toast
3. **Webkit-only mode:** Switch to webkit-only → verify button still appears and works
4. **Double-click prevention:** Click button twice rapidly → verify only one sequence runs
5. **Queue interaction:** Queue a different payload first → click Quick Launch → verify Quick Launch payloads queue after
6. **Toasts:** Verify individual payload toasts are suppressed during Quick Launch
7. **Flag cleanup:** After sequence completes or fails, verify `quickLaunchInProgress` is cleared
