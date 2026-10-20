// @ts-check

/** Saved payload ordering and Quick Launch controls for normal Settings. */
(function () {
    function clear(element) {
        while (element.firstChild) element.removeChild(element.firstChild);
    }

    function status(id, message, failed) {
        var element = document.getElementById(id);
        element.textContent = message;
        element.classList.toggle('launch-settings-error', !!failed);
    }

    function button(text, id, label, action, disabled) {
        var element = document.createElement('button');
        element.type = 'button';
        element.textContent = text;
        element.id = id;
        element.setAttribute('aria-label', label);
        element.disabled = !!disabled;
        element.addEventListener('click', action);
        return element;
    }

    function focusControl(id, fallbackId) {
        var element = document.getElementById(id);
        if (!element || element.disabled) element = document.getElementById(fallbackId || '');
        if (element && !element.disabled) element.focus();
    }

    function renderOrder(focusId, fallbackId) {
        var list = document.getElementById('payload-order-list');
        clear(list);
        var payloads = getOrderedPayloads();
        payloads.forEach(function (payload, index) {
            var row = document.createElement('li');
            row.className = 'launch-settings-row';
            var title = document.createElement('span');
            title.className = 'launch-settings-title';
            title.textContent = (index + 1) + '. ' + payload.displayTitle;
            row.appendChild(title);
            var controls = document.createElement('div');
            controls.className = 'launch-settings-row-actions';
            function move(delta) {
                var ids = getPayloadOrder();
                var from = ids.indexOf(payload.id);
                var to = from + delta;
                if (from < 0 || to < 0 || to >= ids.length) return;
                ids.splice(from, 1);
                ids.splice(to, 0, payload.id);
                var saved = setPayloadOrder(ids);
                status('payload-order-status', saved ? 'Payload order saved.' : 'Could not save payload order. Browser storage may be unavailable.', !saved);
                renderOrder('payload-order-' + (delta < 0 ? 'up-' : 'down-') + payload.id,
                    'payload-order-' + (delta < 0 ? 'down-' : 'up-') + payload.id);
                if (saved) populateSettingsGrid();
            }
            controls.appendChild(button('Up', 'payload-order-up-' + payload.id,
                'Move ' + payload.displayTitle + ' up', function () { move(-1); }, index === 0));
            controls.appendChild(button('Down', 'payload-order-down-' + payload.id,
                'Move ' + payload.displayTitle + ' down', function () { move(1); }, index === payloads.length - 1));
            row.appendChild(controls);
            list.appendChild(row);
        });
        if (focusId) focusControl(focusId, fallbackId);
    }

    function payloadById(id) {
        return payload_map.find(function (payload) { return payload.id === id; });
    }

    function eligible(payload) {
        return !payload.customAction && !payload.willHideEveryTime && payload.versions && payload.versions.length > 0;
    }

    function optionLabel(payload) {
        var label = payload.displayTitle;
        if (!isFirmwareCompatible(payload)) label += ' (Incompatible)';
        if (!payload.toPort) label += ' (Full jailbreak)';
        return label;
    }

    function addOption(select, value, text, disabled) {
        var option = document.createElement('option');
        option.value = value;
        option.textContent = text;
        option.disabled = !!disabled;
        select.appendChild(option);
    }

    function fillChoices(select, selectedId, ids) {
        var found = false;
        getOrderedPayloads().forEach(function (payload) {
            if (payload.id !== selectedId && ids.indexOf(payload.id) !== -1) return;
            if (!eligible(payload) && payload.id !== selectedId) return;
            var compatible = isFirmwareCompatible(payload);
            addOption(select, payload.id, eligible(payload) ? optionLabel(payload) : payload.displayTitle + ' (Unavailable)',
                payload.id !== selectedId && (!eligible(payload) || !compatible));
            if (payload.id === selectedId) found = true;
        });
        if (selectedId && !found) addOption(select, selectedId, selectedId + ' (Unavailable)', false);
        if (selectedId) select.value = selectedId;
    }

    function saveQuickLaunch(next, focusId, fallbackId) {
        var saved = setQuickLaunchSettings(next);
        status('quick-launch-settings-status', saved ? 'Quick Launch saved.' : 'Could not save Quick Launch. Browser storage may be unavailable.', !saved);
        renderQuickLaunch(focusId, fallbackId);
        return saved;
    }

    function renderQuickLaunch(focusId, fallbackId) {
        var config = getQuickLaunchSettings();
        var enabled = document.getElementById('quick-launch-enabled');
        var versions = document.getElementById('quick-launch-selected-versions');
        var delay = document.getElementById('quick-launch-delay');
        enabled.checked = config.enabled;
        versions.checked = config.useSelectedVersions;
        delay.value = String(config.delayMs / 1000);
        var planError = config.enabled && typeof getQuickLaunchPlan === 'function' ? getQuickLaunchPlan(false).error : '';
        var planMessage = !config.enabled ? 'Quick Launch button is hidden.' : planError ||
            config.payloadIds.length + ' steps configured, with a ' + (config.delayMs / 1000) + '-second delay after each completed send.';
        status('quick-launch-plan-status', planMessage, !!planError);
        var list = document.getElementById('quick-launch-steps');
        clear(list);
        config.payloadIds.forEach(function (id, index) {
            var row = document.createElement('li');
            row.className = 'launch-settings-row';
            var label = document.createElement('label');
            label.className = 'launch-settings-step';
            label.textContent = 'Step ' + (index + 1);
            var select = document.createElement('select');
            select.id = 'quick-launch-step-' + index;
            select.setAttribute('aria-label', 'Payload for Quick Launch step ' + (index + 1));
            fillChoices(select, id, config.payloadIds);
            select.addEventListener('change', function () {
                var next = getQuickLaunchSettings();
                var payload = payloadById(select.value);
                if (!payload || !eligible(payload) || !isFirmwareCompatible(payload)) {
                    status('quick-launch-settings-status', 'Choose an available payload compatible with this firmware.', true);
                    renderQuickLaunch(select.id);
                    return;
                }
                next.payloadIds[index] = select.value;
                saveQuickLaunch(next, select.id);
            });
            label.appendChild(select);
            row.appendChild(label);
            var controls = document.createElement('div');
            controls.className = 'launch-settings-row-actions';
            function move(delta) {
                var next = getQuickLaunchSettings();
                var to = index + delta;
                if (to < 0 || to >= next.payloadIds.length) return;
                var moved = next.payloadIds.splice(index, 1)[0];
                next.payloadIds.splice(to, 0, moved);
                saveQuickLaunch(next, 'quick-launch-' + (delta < 0 ? 'up-' : 'down-') + to,
                    'quick-launch-' + (delta < 0 ? 'down-' : 'up-') + to);
            }
            var payload = payloadById(id);
            var title = payload ? payload.displayTitle : id;
            controls.appendChild(button('Up', 'quick-launch-up-' + index, 'Move ' + title + ' up',
                function () { move(-1); }, index === 0));
            controls.appendChild(button('Down', 'quick-launch-down-' + index, 'Move ' + title + ' down',
                function () { move(1); }, index === config.payloadIds.length - 1));
            controls.appendChild(button('Remove', 'quick-launch-remove-' + index, 'Remove ' + title + ' from Quick Launch', function () {
                var next = getQuickLaunchSettings();
                next.payloadIds.splice(index, 1);
                var remaining = Math.min(index, next.payloadIds.length - 1);
                saveQuickLaunch(next, 'quick-launch-step-' + remaining, 'quick-launch-add-payload');
            }));
            row.appendChild(controls);
            list.appendChild(row);
        });
        if (!config.payloadIds.length) {
            var empty = document.createElement('li');
            empty.className = 'launch-settings-help';
            empty.textContent = 'No payloads selected. Add a step to use Quick Launch.';
            list.appendChild(empty);
        }
        var add = document.getElementById('quick-launch-add-payload');
        clear(add);
        addOption(add, '', 'Choose a payload', false);
        fillChoices(add, '', config.payloadIds);
        add.value = '';
        document.getElementById('quick-launch-add').disabled = true;
        if (focusId) focusControl(focusId, fallbackId);
    }

    function initializeLaunchSettings() {
        var order = document.getElementById('payload-order-list');
        if (!order) return;
        renderOrder();
        renderQuickLaunch();
        document.getElementById('payload-order-reset').onclick = function () {
            var saved = resetPayloadOrder();
            status('payload-order-status', saved ? 'Default payload order restored.' : 'Could not reset payload order. Browser storage may be unavailable.', !saved);
            renderOrder('payload-order-reset');
            if (saved) populateSettingsGrid();
        };
        document.getElementById('quick-launch-enabled').onchange = function () {
            var next = getQuickLaunchSettings();
            next.enabled = this.checked;
            saveQuickLaunch(next, this.id);
        };
        document.getElementById('quick-launch-selected-versions').onchange = function () {
            var next = getQuickLaunchSettings();
            next.useSelectedVersions = this.checked;
            saveQuickLaunch(next, this.id);
        };
        document.getElementById('quick-launch-delay').onchange = function () {
            var seconds = Number(this.value);
            if (!this.value.trim() || !isFinite(seconds) || seconds < 0 || seconds > 30 || seconds * 2 !== Math.round(seconds * 2)) {
                status('quick-launch-settings-status', 'Enter a delay from 0 to 30 seconds in half-second steps.', true);
                renderQuickLaunch(this.id);
                return;
            }
            var next = getQuickLaunchSettings();
            next.delayMs = seconds * 1000;
            saveQuickLaunch(next, this.id);
        };
        document.getElementById('quick-launch-add-payload').onchange = function () {
            document.getElementById('quick-launch-add').disabled = !this.value;
        };
        document.getElementById('quick-launch-add').onclick = function () {
            var next = getQuickLaunchSettings();
            var id = document.getElementById('quick-launch-add-payload').value;
            var payload = payloadById(id);
            if (!payload || !eligible(payload) || !isFirmwareCompatible(payload) || next.payloadIds.indexOf(id) !== -1) return;
            next.payloadIds.push(id);
            saveQuickLaunch(next, 'quick-launch-step-' + (next.payloadIds.length - 1));
        };
        document.getElementById('quick-launch-reset').onclick = function () {
            var saved = resetQuickLaunchSettings();
            status('quick-launch-settings-status', saved ? 'Default Quick Launch restored.' : 'Could not reset Quick Launch. Browser storage may be unavailable.', !saved);
            renderQuickLaunch(this.id);
        };
    }

    window.initializeLaunchSettings = initializeLaunchSettings;
})();
