// @ts-check

/**
 * Check if a payload is compatible with the current firmware.
 * Developer mode bypass allows all payloads.
 * @param {Object} payload - The payload object from payload_map
 * @returns {boolean}
 */
function isFirmwareCompatible(payload) {
    // Developer mode bypass
    if (window.devOptions.bypassFirmware) {
        return true;
    }
    
    // No maintained restriction = do not filter. This is not hardware verification.
    if (!payload.supportedFirmwares || payload.supportedFirmwares.length === 0) {
        return true;
    }
    
    // Only a trailing dot denotes a major family. Full firmware versions are exact.
    const currentFw = window.fw_str || "";
    return payload.supportedFirmwares.some(rule =>
        rule.endsWith('.') ? currentFw.startsWith(rule) : currentFw === rule
    );
}

// Export to global scope
window.isFirmwareCompatible = isFirmwareCompatible;
