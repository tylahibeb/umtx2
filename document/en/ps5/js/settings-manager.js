// @ts-check

/**
 * Payload visibility settings (payloadId → boolean).
 * @type {Object<string, boolean>}
 */
let payloadVisibility = {};

/**
 * Payload version overrides (payloadId → versionString).
 * @type {Object<string, string>}
 */
let payloadVersions = {};

/** Saved display order; newly added payloads are appended in catalog order. */
let payloadOrder = [];
let quickLaunchSettings = defaultQuickLaunchSettings();

function defaultQuickLaunchSettings() {
    return {
        enabled: true,
        payloadIds: ["kstuff-lite", "shadowmountplus", "cheatrunner"],
        delayMs: 3000,
        useSelectedVersions: false
    };
}

/** Read each preference independently so one corrupt value cannot erase others. */
function readStoredSetting(key, fallback) {
    try {
        var saved = localStorage.getItem(key);
        return saved === null ? fallback : JSON.parse(saved);
    } catch (error) {
        console.error("Error loading setting " + key + ":", error);
        return fallback;
    }
}

function isSettingsObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isPayloadIdList(value) {
    return Array.isArray(value) && value.every(function (id) {
        return typeof id === "string" && id.length > 0;
    });
}

function uniquePayloadIds(ids) {
    return ids.filter(function (id, index) { return ids.indexOf(id) === index; });
}

function normalizeQuickLaunchSettings(value) {
    if (!isSettingsObject(value) || typeof value.enabled !== "boolean" ||
        typeof value.useSelectedVersions !== "boolean" || !isPayloadIdList(value.payloadIds) ||
        typeof value.delayMs !== "number" || !isFinite(value.delayMs) ||
        value.delayMs < 0 || value.delayMs > 30000) return null;
    return {
        enabled: value.enabled,
        payloadIds: uniquePayloadIds(value.payloadIds),
        delayMs: value.delayMs,
        useSelectedVersions: value.useSelectedVersions
    };
}

/** Keep the active choice unchanged if browser storage rejects a write. */
function persistLaunchSetting(key, value) {
    try {
        var serialized = JSON.stringify(value);
        localStorage.setItem(key, serialized);
        if (localStorage.getItem(key) !== serialized) throw new Error("Preference was not saved");
        return true;
    } catch (error) {
        console.error("Error saving setting " + key + ":", error);
        return false;
    }
}

function removeLaunchSetting(key) {
    try {
        localStorage.removeItem(key);
        if (localStorage.getItem(key) !== null) throw new Error("Preference was not reset");
        return true;
    } catch (error) {
        console.error("Error resetting setting " + key + ":", error);
        return false;
    }
}

/**
 * Load settings from localStorage.
 */
function loadSettings() {
    var visibility = readStoredSetting(window.SETTINGS_PAYLOAD_VISIBILITY, {});
    var versions = readStoredSetting(window.SETTINGS_PAYLOAD_VERSIONS, {});
    var order = readStoredSetting(window.SETTINGS_PAYLOAD_ORDER, []);
    var quickLaunch = readStoredSetting(window.SETTINGS_QUICK_LAUNCH, null);
    payloadVisibility = isSettingsObject(visibility) ? visibility : {};
    payloadVersions = isSettingsObject(versions) ? versions : {};
    payloadOrder = isPayloadIdList(order) ? uniquePayloadIds(order) : [];
    quickLaunchSettings = normalizeQuickLaunchSettings(quickLaunch) || defaultQuickLaunchSettings();
}

/** Unknown/removed IDs are ignored; additions retain the maintained catalog order. */
function getPayloadOrder() {
    var available = typeof payload_map === "undefined" ? [] : payload_map.map(function (p) { return p.id; });
    var saved = payloadOrder.filter(function (id) { return available.indexOf(id) !== -1; });
    return saved.concat(available.filter(function (id) { return saved.indexOf(id) === -1; }));
}

function getOrderedPayloads() {
    if (typeof payload_map === "undefined") return [];
    return getPayloadOrder().map(function (id) {
        return payload_map.find(function (payload) { return payload.id === id; });
    });
}

function setPayloadOrder(ids) {
    if (!isPayloadIdList(ids)) return false;
    var available = typeof payload_map === "undefined" ? [] : payload_map.map(function (p) { return p.id; });
    var order = uniquePayloadIds(ids).filter(function (id) { return available.indexOf(id) !== -1; });
    order = order.concat(available.filter(function (id) { return order.indexOf(id) === -1; }));
    if (!persistLaunchSetting(window.SETTINGS_PAYLOAD_ORDER, order)) return false;
    payloadOrder = order;
    return true;
}

function resetPayloadOrder() {
    if (!removeLaunchSetting(window.SETTINGS_PAYLOAD_ORDER)) return false;
    payloadOrder = [];
    return true;
}

function getQuickLaunchSettings() {
    return {
        enabled: quickLaunchSettings.enabled,
        payloadIds: quickLaunchSettings.payloadIds.slice(),
        delayMs: quickLaunchSettings.delayMs,
        useSelectedVersions: quickLaunchSettings.useSelectedVersions
    };
}

function setQuickLaunchSettings(value) {
    var normalized = normalizeQuickLaunchSettings(value);
    if (!normalized || !persistLaunchSetting(window.SETTINGS_QUICK_LAUNCH, normalized)) return false;
    quickLaunchSettings = normalized;
    return true;
}

function resetQuickLaunchSettings() {
    if (!removeLaunchSetting(window.SETTINGS_QUICK_LAUNCH)) return false;
    quickLaunchSettings = defaultQuickLaunchSettings();
    return true;
}

/**
 * Save settings to localStorage.
 */
function saveSettings() {
    try {
        localStorage.setItem(window.SETTINGS_PAYLOAD_VISIBILITY, JSON.stringify(payloadVisibility));
        localStorage.setItem(window.SETTINGS_PAYLOAD_VERSIONS, JSON.stringify(payloadVersions));
    } catch (e) {
        console.error("Error saving settings:", e);
    }
}

/**
 * Check if a payload is visible.
 * Developer mode override allows showing all payloads.
 * @param {string} payloadId
 * @returns {boolean}
 */
function isPayloadVisible(payloadId) {
    if (window.devOptions.showAllPayloads) {
        return true;
    }
    return payloadVisibility[payloadId] !== false;
}

/**
 * Set payload visibility.
 * @param {string} payloadId
 * @param {boolean} visible
 */
function setPayloadVisible(payloadId, visible) {
    payloadVisibility[payloadId] = visible;
    saveSettings();
}

/**
 * Get selected version for a payload.
 * @param {string} payloadId
 * @returns {string|null}
 */
function getSelectedVersion(payloadId) {
    return payloadVersions[payloadId] || null;
}

/**
 * Set selected version for a payload.
 * @param {string} payloadId
 * @param {string} version
 */
function setSelectedVersion(payloadId, version) {
    if (version) {
        payloadVersions[payloadId] = version;
    } else {
        // Clear stale selection by removing the key entirely
        delete payloadVersions[payloadId];
    }
    saveSettings();
}

/**
 * Resolve the active version info for a payload.
 * Returns filePath (new v2 format) with fallback to fileName (legacy).
 * @param {Object} payload
 * @returns {{version: string, fileName: string, filePath: string}}
 */
function resolveActiveVersion(payload) {
    if (payload.versions && payload.versions.length > 0) {
        const selectedVer = getSelectedVersion(payload.id);
        let verData = null;

        if (selectedVer) {
            verData = payload.versions.find(v => v.version === selectedVer);
        }

        if (!verData) {
            verData = payload.versions.find(v => v.isDefault) || payload.versions[0];
        }

        if (verData) {
            // v2 format: use filePath; fallback to "payloads/" + fileName for legacy
            const filePath = verData.filePath || ("payloads/" + verData.fileName);
            return {
                version: verData.version,
                fileName: verData.fileName,
                filePath: filePath
            };
        }
    }

    // Legacy fallback (should not happen with v2 payload_map.js)
    return {
        version: payload.version || "",
        fileName: payload.fileName || "",
        filePath: payload.fileName ? ("payloads/" + payload.fileName) : ""
    };
}

// Export to global scope
window.loadSettings = loadSettings;
window.saveSettings = saveSettings;
window.isPayloadVisible = isPayloadVisible;
window.setPayloadVisible = setPayloadVisible;
window.getSelectedVersion = getSelectedVersion;
window.setSelectedVersion = setSelectedVersion;
window.resolveActiveVersion = resolveActiveVersion;
window.getPayloadOrder = getPayloadOrder;
window.getOrderedPayloads = getOrderedPayloads;
window.setPayloadOrder = setPayloadOrder;
window.resetPayloadOrder = resetPayloadOrder;
window.getQuickLaunchSettings = getQuickLaunchSettings;
window.setQuickLaunchSettings = setQuickLaunchSettings;
window.resetQuickLaunchSettings = resetQuickLaunchSettings;

// Load settings on script init
loadSettings();
