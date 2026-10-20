// @ts-check

/**
 * Optional offline storage for older PS5 WebKit (Application Cache).
 * Runs in <head>, before the rest of the UI. The online entry has no manifest;
 * only offline.html joins the offline.appcache group. Changing a manifest
 * attribute in JavaScript cannot opt a document in or out of AppCache.
 */
(function () {
    'use strict';

    var storageKey = 'offline_cache_enabled';
    var offlineEntry = document.documentElement.getAttribute('manifest') === 'offline.appcache';
    var listeners = [];
    var cache = null;
    var enabled = false;
    var confirmedReady = false;
    var status = 'off';
    var notice = '';
    var progress = null;

    try {
        cache = window.applicationCache;
    } catch (error) {
        // Some browsers expose a getter that throws outside a supported context.
    }
    var supported = !!(cache && typeof cache.addEventListener === 'function');
    try {
        // Neither the old inverted developer switch nor its default is consent.
        enabled = window.localStorage.getItem(storageKey) === '1';
    } catch (error) {
        status = 'storage-error';
        notice = 'Browser preferences are unavailable. Offline caching is off.';
    }

    function modeUrl(offline) {
        var path = window.location.pathname;
        var directory = path.substring(0, path.lastIndexOf('/') + 1);
        return directory + (offline ? 'offline.html' : 'index.html') +
            window.location.search + window.location.hash;
    }

    function isEnabled() {
        return enabled && supported;
    }

    function isReady() {
        return isEnabled() && offlineEntry && (
            confirmedReady || cache.status === 1 || cache.status === 4
        );
    }

    function getMessage() {
        if (notice) return notice;
        if (!supported) return 'This browser does not support offline caching.';
        if (!enabled) return 'Off — internet is required to open the site.';
        if (status === 'checking') return 'Checking the saved offline copy…';
        if (status === 'downloading') {
            return 'Saving offline files' + (progress === null ? '…' : '… ' + progress + '%');
        }
        if (status === 'update-ready') return 'An updated offline copy is ready. Reload to use it.';
        if (status === 'ready') return 'Ready for offline use. Bookmark this offline page.';
        if (status === 'error') {
            return isReady() ? 'Update failed. The previous saved copy is still available.' :
                'Offline download failed. Stay online and retry the download.';
        }
        if (status === 'obsolete') return 'The saved offline copy is no longer available. Reload while online.';
        return 'Preparing the offline download…';
    }

    function getState() {
        return {
            enabled: isEnabled(),
            supported: supported,
            ready: isReady(),
            status: status,
            message: getMessage(),
            progress: progress,
            offlineUrl: modeUrl(true)
        };
    }

    function publish() {
        var state = getState();
        listeners.slice().forEach(function (listener) {
            listener(state);
        });
    }

    function setStatus(next, message) {
        status = next;
        notice = message || '';
        if (next !== 'downloading') progress = null;
        publish();
    }

    function abortDownload() {
        if (!supported) return;
        try {
            cache.abort();
        } catch (error) {
            // abort() may throw when no update is active; that is already stopped.
        }
    }

    function setEnabled(value) {
        value = value === true;
        if (value && !supported) {
            setStatus('unsupported');
            return false;
        }
        if (value && !isReady() && window.navigator.onLine === false) {
            setStatus('error', 'Connect to the internet before downloading the offline copy.');
            return false;
        }
        if (!value && offlineEntry && window.navigator.onLine === false) {
            setStatus('error', 'Connect to the internet before switching to the online page.');
            return false;
        }
        try {
            var saved = value ? '1' : '0';
            window.localStorage.setItem(storageKey, saved);
            if (window.localStorage.getItem(storageKey) !== saved) throw new Error('Preference not retained');
        } catch (error) {
            setStatus('storage-error', 'Could not save the offline preference. The previous setting is unchanged.');
            return false;
        }
        enabled = value;
        setStatus(value ? 'waiting' : 'off');
        if (!value) abortDownload();
        if (value !== offlineEntry) window.location.replace(modeUrl(value));
        return true;
    }

    function reload() {
        if (supported && offlineEntry && cache.status === 4) {
            try {
                cache.swapCache();
            } catch (error) {
                // A fresh navigation can still select the newest complete cache.
            }
        }
        window.location.reload();
    }

    function checkForUpdates() {
        if (!isEnabled() || !offlineEntry) return false;
        if (cache.status === 2 || cache.status === 3) return false;
        if (cache.status === 0 || cache.status === 5) {
            reload();
            return true;
        }
        try {
            cache.update();
            return true;
        } catch (error) {
            setStatus('error', 'Could not start the offline update. Reload while online to retry.');
            return false;
        }
    }

    window.offlineCache = {
        isEnabled: isEnabled,
        isSupported: function () { return supported; },
        isReady: isReady,
        getState: getState,
        setEnabled: setEnabled,
        checkForUpdates: checkForUpdates,
        reload: reload,
        subscribe: function (listener) {
            listeners.push(listener);
            listener(getState());
            return function () {
                var index = listeners.indexOf(listener);
                if (index !== -1) listeners.splice(index, 1);
            };
        }
    };

    if (supported && offlineEntry) {
        confirmedReady = cache.status === 1 || cache.status === 4;
        if (enabled) {
            var initial = { 0: 'waiting', 1: 'ready', 2: 'checking', 3: 'downloading', 4: 'update-ready', 5: 'obsolete' };
            status = initial[cache.status] || 'waiting';
        }
        ['checking', 'downloading', 'progress', 'cached', 'noupdate', 'updateready', 'error', 'obsolete']
            .forEach(function (name) {
                cache.addEventListener(name, function (event) {
                    if (!enabled) {
                        if (name === 'checking' || name === 'downloading') abortDownload();
                        return;
                    }
                    if (name === 'cached' || name === 'noupdate') {
                        confirmedReady = true;
                        setStatus('ready');
                    } else if (name === 'updateready') {
                        confirmedReady = true;
                        setStatus('update-ready');
                    } else if (name === 'obsolete') {
                        confirmedReady = false;
                        setStatus('obsolete');
                    } else if (name === 'progress') {
                        progress = event.total > 0 ? Math.min(100, Math.round(event.loaded / event.total * 100)) : null;
                        // A progress event is not proof the transaction committed.
                        status = 'downloading';
                        notice = '';
                        publish();
                    } else {
                        setStatus(name);
                    }
                }, false);
            });
    } else if (!supported) {
        status = 'unsupported';
    } else if (enabled && status !== 'storage-error') {
        status = 'waiting';
    }

    // Never attach a manifest to index.html dynamically. The separate entry is
    // what makes opt-in possible. A direct offline URL cannot override opt-out.
    if (offlineEntry && !isEnabled()) {
        abortDownload();
        window.location.replace(modeUrl(false));
    } else if (!offlineEntry && isEnabled()) {
        window.location.replace(modeUrl(true));
    }
}());
