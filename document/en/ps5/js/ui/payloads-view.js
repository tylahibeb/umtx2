// @ts-check

/**
 * Post-JB payloads view.
 * Populates the payloads grid after jailbreak and dispatches payload execution.
 * Version selection is done in Settings, not here - this view only displays the selected version.
 * Depends on: constants, settings-manager, firmware-compat, toast-notifications
 */

/**
 * Populate the post-jailbreak payloads grid.
 * Only shows VISIBLE payloads with their selected versions.
 * Clicking a payload DISPATCHES it for execution (original behavior).
 * Version selection is done in Settings - here we only show the selected version.
 * @param {boolean} [wkOnlyMode=false]
 */
function populatePayloadsPage(wkOnlyMode) {
    if (wkOnlyMode === undefined) wkOnlyMode = false;

    var payloadsView = document.getElementById('payloads-view');

    while (payloadsView.firstChild) {
        payloadsView.removeChild(payloadsView.firstChild);
    }

    // Quick Launch button — dispatches kstuff-lite, ShadowMountPlus, Elf Arsenal sequentially
    // Always show regardless of wkOnlyMode (all payloads send to port 9021 via elfldr)
    // IMPORTANT: etaHEN must ALWAYS be last — it depends on all other payloads being active first.
    var quickLaunchContainer = document.createElement("div");
    quickLaunchContainer.className = "quick-launch-container";

    var quickLaunchBtn = document.createElement("button");
    quickLaunchBtn.className = "quick-launch-btn";
    var quickLaunchIcon = document.createElement("span");
    quickLaunchIcon.className = "quick-launch-icon";
    quickLaunchIcon.textContent = "⚡";
    var quickLaunchLabel = document.createElement("span");
    quickLaunchLabel.textContent = "Quick Launch";

    var quickLaunchSubtitle = document.createElement("p");
    quickLaunchSubtitle.className = "quick-launch-subtitle";
    quickLaunchSubtitle.textContent = "kstuff-lite + ShadowMountPlus + Elf Arsenal";

    quickLaunchBtn.appendChild(quickLaunchIcon);
    quickLaunchBtn.appendChild(quickLaunchLabel);
    quickLaunchBtn.appendChild(quickLaunchSubtitle);
    quickLaunchContainer.appendChild(quickLaunchBtn);
    payloadsView.appendChild(quickLaunchContainer);

    quickLaunchBtn.addEventListener("click", function () {
        if (window.quickLaunchInProgress) return;
        window.quickLaunchInProgress = true;
        window.quickLaunchFailed = false;
        this.classList.add("quick-launch-btn--loading");
        var self = this;
        startQuickLaunch(function onComplete() {
            self.classList.remove("quick-launch-btn--loading");
        });
    });

    for (var i = 0; i < payload_map.length; i++) {
        var payload = payload_map[i];

        if (wkOnlyMode && !payload.toPort && !payload.customAction) {
            continue;
        }

        // Use isFirmwareCompatible which respects dev mode bypass
        if (!isFirmwareCompatible(payload)) {
            continue;
        }

        // Skip payloads marked as willHideEveryTime - never show in UI under any circumstance
        if (payload.willHideEveryTime) {
            continue;
        }

        // Skip hidden payloads - they don't show in post-JB view
        if (!isPayloadVisible(payload.id)) {
            continue;
        }

        // Resolve active version
        var versionInfo = resolveActiveVersion(payload);
        var activeVersion = versionInfo.version;
        var activeFileName = versionInfo.fileName;
        var activeFilePath = versionInfo.filePath;

        var payloadButton = document.createElement("a");
        payloadButton.classList.add("btn");
        payloadButton.classList.add("w-100");
        payloadButton.tabIndex = 0;
        payloadButton.style.position = "relative";

        var payloadTitle = document.createElement("p");
        payloadTitle.classList.add("payload-btn-title");
        payloadTitle.textContent = payload.displayTitle;

        // Always show selected version as inline text badge
        // Version selection is done in Settings, not here
        var fwVersion = document.createElement("span");
        fwVersion.className = "fw-version";
        fwVersion.textContent = "v" + activeVersion;
        payloadTitle.appendChild(fwVersion);

        var payloadDescription = document.createElement("p");
        payloadDescription.classList.add("payload-btn-description");
        payloadDescription.textContent = payload.description;

        var payloadInfo = document.createElement("p");
        payloadInfo.classList.add("payload-btn-info");
        payloadInfo.textContent = payload.author;

        payloadButton.appendChild(payloadTitle);
        payloadButton.appendChild(payloadDescription);
        payloadButton.appendChild(payloadInfo);

        // Store active version as data attributes for dispatch
        payloadButton.setAttribute("data-active-version", activeVersion);
        payloadButton.setAttribute("data-active-filename", activeFileName);
        payloadButton.setAttribute("data-active-filepath", activeFilePath);

        // Click → DISPATCH PAYLOAD FOR EXECUTION (original behavior)
        // Read the currently active version from data attributes (may have been changed by dropdown)
        (function (p) {
            payloadButton.addEventListener("click", function () {
                var btn = this;
                var resolvedVer = btn.getAttribute("data-active-version") || activeVersion;
                var resolvedFn = btn.getAttribute("data-active-filename") || activeFileName;
                var resolvedFp = btn.getAttribute("data-active-filepath") || activeFilePath;

                // Create a copy with resolved version/fileName/filePath for dispatch
                var resolvedPayload = {};
                for (var key in p) {
                    resolvedPayload[key] = p[key];
                }
                resolvedPayload.version = resolvedVer;
                resolvedPayload.fileName = resolvedFn;
                resolvedPayload.filePath = resolvedFp;
                window.dispatchEvent(new CustomEvent(MAINLOOP_EXECUTE_PAYLOAD_REQUEST, { detail: resolvedPayload }));
            });
        })(payload);

        payloadsView.appendChild(payloadButton);
    }
}

// Quick Launch: sequential dispatcher for kstuff-lite, ShadowMountPlus, Elf Arsenal
// Elf Arsenal is launched last so it builds on top of kstuff-lite's kernel patches
// and ShadowMountPlus's mounts (Arsenal bundles its own nanoDNS internally).
var QUICK_LAUNCH_PAYLOADS = ["kstuff-lite", "shadowmountplus", "elf-arsenal"];
var QUICK_LAUNCH_DELAY_MS = 3000;

function startQuickLaunch(onComplete) {
    var toast = showToast("Quick Launch: Starting...", -1);
    window.quickLaunchToast = toast;

    var dispatched = 0;

    function finishSequence(success) {
        window.quickLaunchInProgress = false;
        window.quickLaunchFailed = !success;
        window.quickLaunchToast = null;
        if (onComplete) onComplete();
    }

    function dispatchNext() {
        if (window.quickLaunchFailed) {
            // Error occurred in main loop — button cleanup handled by finishSequence
            finishSequence(false);
            return;
        }
        if (dispatched >= QUICK_LAUNCH_PAYLOADS.length) {
            return;
        }

        var payloadId = QUICK_LAUNCH_PAYLOADS[dispatched];
        var payload = payload_map.find(function (p) { return p.id === payloadId; });

        if (!payload) {
            updateToastMessage(toast, "Quick Launch: Failed ❌ — payload '" + payloadId + "' not found");
            setTimeout(function () {
                removeToast(toast);
                finishSequence(false);
            }, TOAST_ERROR_TIMEOUT);
            return;
        }

        // Resolve default version (always use isDefault, ignoring user Settings selection)
        var defaultVer = payload.versions.find(function (v) { return v.isDefault; }) || payload.versions[0];
        var filePath = defaultVer.filePath || ("payloads/" + payload.id + "/" + defaultVer.version + "/" + defaultVer.fileName);

        var resolvedPayload = {};
        for (var key in payload) {
            resolvedPayload[key] = payload[key];
        }
        resolvedPayload.version = defaultVer.version;
        resolvedPayload.fileName = defaultVer.fileName;
        resolvedPayload.filePath = filePath;

        updateToastMessage(toast, "Quick Launch: " + payload.displayTitle + " (" + (dispatched + 1) + "/" + QUICK_LAUNCH_PAYLOADS.length + ")");

        window.dispatchEvent(new CustomEvent(MAINLOOP_EXECUTE_PAYLOAD_REQUEST, { detail: resolvedPayload }));

        dispatched++;

        if (dispatched >= QUICK_LAUNCH_PAYLOADS.length) {
            // All dispatched — main loop processes them
            updateToastMessage(toast, "Quick Launch: All dispatched ✅ (" + QUICK_LAUNCH_PAYLOADS.length + "/" + QUICK_LAUNCH_PAYLOADS.length + ")");
            setTimeout(function () {
                removeToast(toast);
                finishSequence(true);
            }, TOAST_SUCCESS_TIMEOUT);
        } else {
            setTimeout(dispatchNext, QUICK_LAUNCH_DELAY_MS);
        }
    }

    dispatchNext();
}

// Export to global scope
window.populatePayloadsPage = populatePayloadsPage;
window.startQuickLaunch = startQuickLaunch;
