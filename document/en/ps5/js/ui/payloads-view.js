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

    var launchSettings = getQuickLaunchSettings();
    if (launchSettings.enabled) {
        var launchPlan = getQuickLaunchPlan(wkOnlyMode);
        var quickLaunchContainer = document.createElement("div");
        quickLaunchContainer.className = "quick-launch-container";

        var quickLaunchBtn = document.createElement("button");
        quickLaunchBtn.className = "quick-launch-btn";
        quickLaunchBtn.type = "button";
        quickLaunchBtn.disabled = !!launchPlan.error || !!window.quickLaunchInProgress;
        var quickLaunchIcon = document.createElement("span");
        quickLaunchIcon.className = "quick-launch-icon";
        quickLaunchIcon.textContent = "⚡";
        var quickLaunchLabel = document.createElement("span");
        quickLaunchLabel.textContent = "Quick Launch";

        var quickLaunchSubtitle = document.createElement("p");
        quickLaunchSubtitle.className = "quick-launch-subtitle";
        quickLaunchSubtitle.textContent = launchPlan.error ? launchPlan.error + " Change Quick Launch in Settings." :
            launchPlan.payloads.map(function (payload) { return payload.displayTitle; }).join(" + ");

        quickLaunchBtn.appendChild(quickLaunchIcon);
        quickLaunchBtn.appendChild(quickLaunchLabel);
        quickLaunchBtn.appendChild(quickLaunchSubtitle);
        quickLaunchContainer.appendChild(quickLaunchBtn);
        payloadsView.appendChild(quickLaunchContainer);

        quickLaunchBtn.addEventListener("click", function () {
            if (window.quickLaunchInProgress) return;
            this.classList.add("quick-launch-btn--loading");
            this.disabled = true;
            var self = this;
            startQuickLaunch(function onComplete() {
                self.classList.remove("quick-launch-btn--loading");
                self.disabled = !!getQuickLaunchPlan(wkOnlyMode).error;
            }, wkOnlyMode);
        });
    }

    var orderedPayloads = getOrderedPayloads();
    for (var i = 0; i < orderedPayloads.length; i++) {
        var payload = orderedPayloads[i];

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

/**
 * Resolve and validate the entire saved launch sequence before sending anything.
 * A missing prerequisite must not silently disappear from the sequence.
 * Hidden ordinary payloads are allowed because the sequence explicitly selects them.
 * @param {boolean} [wkOnlyMode=false]
 * @returns {{payloads: Object[], delayMs: number, error: string}}
 */
function getQuickLaunchPlan(wkOnlyMode) {
    var settings = getQuickLaunchSettings();
    var plan = { payloads: [], delayMs: settings.delayMs, error: "" };
    if (!settings.enabled) {
        plan.error = "Quick Launch is turned off.";
        return plan;
    }
    if (!settings.payloadIds.length) {
        plan.error = "Choose at least one Quick Launch payload.";
        return plan;
    }

    for (var i = 0; i < settings.payloadIds.length; i++) {
        var payloadId = settings.payloadIds[i];
        var payload = payload_map.find(function (entry) { return entry.id === payloadId; });
        if (!payload) {
            plan.error = "Payload '" + payloadId + "' is unavailable.";
            break;
        }
        if (payload.willHideEveryTime || payload.customAction) {
            plan.error = payload.displayTitle + " cannot be used in Quick Launch.";
            break;
        }
        if (!isFirmwareCompatible(payload)) {
            plan.error = payload.displayTitle + " is incompatible with this firmware.";
            break;
        }
        if (wkOnlyMode && !payload.toPort) {
            plan.error = payload.displayTitle + " requires the full jailbreak.";
            break;
        }
        if (!payload.versions || !payload.versions.length) {
            plan.error = payload.displayTitle + " has no available version.";
            break;
        }

        var versionInfo = settings.useSelectedVersions ? resolveActiveVersion(payload) :
            payload.versions.find(function (version) { return version.isDefault; }) || payload.versions[0];
        if (!versionInfo || (!versionInfo.filePath && !versionInfo.fileName)) {
            plan.error = payload.displayTitle + " has no payload file.";
            break;
        }

        var resolvedPayload = {};
        for (var key in payload) resolvedPayload[key] = payload[key];
        resolvedPayload.version = versionInfo.version;
        resolvedPayload.fileName = versionInfo.fileName;
        resolvedPayload.filePath = versionInfo.filePath ||
            ("payloads/" + payload.id + "/" + versionInfo.version + "/" + versionInfo.fileName);
        plan.payloads.push(resolvedPayload);
    }
    if (plan.error) plan.payloads = [];
    return plan;
}

var quickLaunchRunCounter = 0;

/**
 * Send each payload only after its predecessor completes successfully. The delay
 * starts after delivery/execution, not while the preceding file is downloading.
 * A successful send does not confirm the receiving application is ready.
 * @param {function(boolean): void} [onComplete]
 * @param {boolean} [wkOnlyMode=false]
 * @returns {boolean} Whether a launch was accepted.
 */
function startQuickLaunch(onComplete, wkOnlyMode) {
    if (window.quickLaunchInProgress) return false;
    var plan = getQuickLaunchPlan(wkOnlyMode);
    if (plan.error) {
        showToast("Quick Launch: " + plan.error, TOAST_ERROR_TIMEOUT);
        if (onComplete) onComplete(false);
        return false;
    }

    var toast = showToast("Quick Launch: Starting...", -1);
    var runId = ++quickLaunchRunCounter;
    var completed = 0;
    var waitingRequestId = null;
    var delayTimer = null;
    var finished = false;
    window.quickLaunchInProgress = true;
    window.quickLaunchFailed = false;
    window.quickLaunchToast = toast;

    function finishSequence(success, message) {
        if (finished) return;
        finished = true;
        if (delayTimer !== null) clearTimeout(delayTimer);
        window.removeEventListener(MAINLOOP_PAYLOAD_RESULT, onPayloadResult);
        window.quickLaunchInProgress = false;
        window.quickLaunchFailed = !success;
        window.quickLaunchToast = null;
        updateToastMessage(toast, message);
        setTimeout(function () { removeToast(toast); }, success ? TOAST_SUCCESS_TIMEOUT : TOAST_ERROR_TIMEOUT);
        if (onComplete) onComplete(success);
    }

    function onPayloadResult(event) {
        var result = event.detail;
        if (finished || !result || !waitingRequestId || result.requestId !== waitingRequestId) return;
        waitingRequestId = null;
        if (!result.success) {
            finishSequence(false, "Quick Launch: Failed — " + plan.payloads[completed].displayTitle +
                (result.error ? ": " + result.error : ""));
            return;
        }
        completed++;
        if (completed === plan.payloads.length) {
            finishSequence(true, "Quick Launch: All payloads sent/completed (" + completed + "/" + plan.payloads.length + ")");
        } else {
            updateToastMessage(toast, "Quick Launch: Waiting " + (plan.delayMs / 1000) + "s before " +
                plan.payloads[completed].displayTitle + " (" + (completed + 1) + "/" + plan.payloads.length + ")");
            delayTimer = setTimeout(dispatchNext, plan.delayMs);
        }
    }

    function dispatchNext() {
        if (finished) return;
        delayTimer = null;
        var payload = plan.payloads[completed];
        waitingRequestId = "quick-launch-" + runId + "-" + completed;
        payload.quickLaunchRequestId = waitingRequestId;
        updateToastMessage(toast, "Quick Launch: " + payload.displayTitle + " (" + (completed + 1) + "/" + plan.payloads.length + ")");
        window.dispatchEvent(new CustomEvent(MAINLOOP_EXECUTE_PAYLOAD_REQUEST, { detail: payload }));
    }

    window.addEventListener(MAINLOOP_PAYLOAD_RESULT, onPayloadResult);
    dispatchNext();
    return true;
}

// Export to global scope
window.populatePayloadsPage = populatePayloadsPage;
window.getQuickLaunchPlan = getQuickLaunchPlan;
window.startQuickLaunch = startQuickLaunch;
