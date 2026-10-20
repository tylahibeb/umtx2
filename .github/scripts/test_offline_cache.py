#!/usr/bin/env python3
"""Regressions for opt-in AppCache generation, routing and browser state."""

import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
GENERATOR = REPO_ROOT / "appcache_manifest_generator.py"


def run_node(script):
    node = shutil.which("node")
    if not node:
        raise AssertionError("Node.js is required for offline cache regressions")
    result = subprocess.run(
        [node, "-e", script, str(REPO_ROOT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)


class ManifestGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.index = (
            '<html>\n<head><script src="js/cache-controller.js"></script></head>\n'
            '<body>Example host</body>\n</html>\n'
        )
        self.write("index.html", self.index)
        self.write("main.css", "body { color: white; }\n")
        self.write("js/cache-controller.js", "window.example = true;\n")
        self.write("other.html", "<html>Unrelated page</html>\n")
        self.write("payloads/example/1.0/example.elf", b"\x7fELFdefault")
        self.write("payloads/example/0.9/example.elf", b"\x7fELFolder")
        self.write(
            "payloads/example/metadata.json",
            json.dumps({
                "id": "example",
                "versions": [
                    {
                        "version": "1.0", "isDefault": True,
                        "filePath": "payloads/example/1.0/example.elf",
                        "changelog": ["Fix JSON options: {hello: world}"],
                    },
                    {
                        "version": "0.9", "isDefault": False,
                        "filePath": "payloads/example/0.9/example.elf",
                    },
                ],
            }),
        )
        self.write("cache.appcache", "CACHE MANIFEST\nlegacy\n")

    def write(self, path, contents):
        target = self.directory / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(contents, bytes):
            target.write_bytes(contents)
        else:
            target.write_text(contents)

    def generate(self, *flags):
        result = subprocess.run(
            [sys.executable, str(GENERATOR), "-d", str(self.directory), *flags],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def manifest_entries(self):
        entries = {}
        for line in (self.directory / "offline.appcache").read_text().splitlines():
            if " #" in line:
                name, digest = line.rsplit(" #", 1)
                entries[name] = digest
        return entries

    def test_generation_keeps_online_entry_manifest_free_and_is_repeatable(self):
        self.generate()
        self.assertEqual((self.directory / "index.html").read_text(), self.index)
        offline = (self.directory / "offline.html").read_text()
        self.assertRegex(offline, r'<html\b[^>]*\bmanifest=["\']offline\.appcache["\']')
        self.assertFalse((self.directory / "cache.appcache").exists())
        before = {
            path: (self.directory / path).read_bytes()
            for path in ["index.html", "offline.html", "offline.appcache"]
        }
        self.generate()
        for path, content in before.items():
            self.assertEqual((self.directory / path).read_bytes(), content, path)

    def test_manifest_caches_only_offline_entry_and_default_binary(self):
        self.generate()
        entries = self.manifest_entries()
        for name in [
            "offline.html", "main.css", "js/cache-controller.js",
            "payloads/example/metadata.json", "payloads/example/1.0/example.elf",
        ]:
            self.assertIn(name, entries)
        for name in ["index.html", "/", "./", "other.html", "payloads/example/0.9/example.elf"]:
            self.assertNotIn(name, entries)
        for name, digest in entries.items():
            self.assertEqual(
                hashlib.sha256((self.directory / name).read_bytes()).hexdigest(),
                digest, name,
            )

    def test_generator_import_does_not_parse_cli_or_write_files(self):
        result = subprocess.run(
            [
                sys.executable, "-c",
                "import runpy,sys; sys.argv=['generator','--not-a-real-option']; "
                "runpy.run_path(" + repr(str(GENERATOR)) +
                ", run_name='offline_cache_import')",
            ],
            cwd=self.directory,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.directory / "offline.html").exists())


class GeneratedSiteTests(unittest.TestCase):
    def test_checked_in_offline_artifacts_match_online_source_and_metadata(self):
        site = REPO_ROOT / "document/en/ps5"
        online = (site / "index.html").read_text()
        opening = re.search(r"<html\b[^>]*>", online, re.I)
        self.assertIsNotNone(opening)
        self.assertNotRegex(opening.group(), r"\bmanifest\s*=")
        expected = re.sub(
            r"(<html\b)", r'\1 manifest="offline.appcache"',
            online, count=1, flags=re.I,
        )
        self.assertEqual((site / "offline.html").read_text(), expected)
        self.assertFalse((site / "cache.appcache").exists())
        entries = {}
        lines = (site / "offline.appcache").read_text().splitlines()
        self.assertEqual(lines[0], "CACHE MANIFEST")
        for line in lines[1:]:
            if line == "NETWORK:":
                break
            if not line or line.startswith("#"):
                continue
            self.assertIn(" #", line)
            name, digest = line.rsplit(" #", 1)
            self.assertNotIn(name, entries, "Duplicate offline resource")
            self.assertFalse(Path(name).is_absolute())
            self.assertNotIn("..", Path(name).parts)
            source = site / name
            self.assertTrue(source.is_file(), name)
            checksum = hashlib.sha256()
            with source.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    checksum.update(chunk)
            self.assertEqual(checksum.hexdigest(), digest, name)
            entries[name] = digest
        self.assertEqual(
            {name for name in entries if Path(name).suffix.lower() in {".html", ".htm"}},
            {"offline.html"},
        )
        self.assertNotIn("/", entries)
        self.assertNotIn("./", entries)
        self.assertNotIn("offline.appcache", entries)
        for script in re.findall(r'<script\b[^>]*\bsrc=["\']([^"\']+)["\']', online):
            self.assertIn(script, entries, "Shared script missing from offline cache")
        defaults = set()
        for metadata_path in (site / "payloads").glob("*/metadata.json"):
            metadata = json.loads(metadata_path.read_text())
            for version in metadata["versions"]:
                if version.get("isDefault") is True and version.get("filePath"):
                    defaults.add(version["filePath"])
        self.assertGreater(len(defaults), 0)
        cached_binaries = {
            name for name in entries if Path(name).suffix.lower() in {".elf", ".bin"}
        }
        self.assertEqual(cached_binaries, defaults)


NODE_HARNESS = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = process.argv[1];
const source = fs.readFileSync(path.join(root,
    'document/en/ps5/js/cache-controller.js'), 'utf8');
function boot(options = {}) {
    const events = [], listeners = {}, navigations = [];
    const stored = Object.assign({}, options.storage || {});
    const attributes = Object.assign({}, options.manifest
        ? {manifest: options.manifest} : {});
    let current = new URL(options.url || 'https://example.test/umtx2/index.html');
    function navigate(value) {
        const target = new URL(value, current.href).href;
        events.push(['navigate', target]);
        navigations.push(target);
        current = new URL(target);
    }
    const location = {
        replace: navigate, assign: navigate,
        reload() { events.push(['reload']); },
    };
    for (const key of ['href', 'pathname', 'search', 'hash', 'origin']) {
        Object.defineProperty(location, key, {
            get: () => current[key],
            set: value => key === 'href' ? navigate(value) : (current[key] = value),
        });
    }
    const appCache = {
        UNCACHED: 0, IDLE: 1, CHECKING: 2, DOWNLOADING: 3,
        UPDATEREADY: 4, OBSOLETE: 5,
        status: options.status === undefined ? 0 : options.status,
        updateCalls: 0, abortCalls: 0,
        addEventListener(name, fn) { (listeners[name] ||= []).push(fn); },
        removeEventListener(name, fn) {
            listeners[name] = (listeners[name] || []).filter(item => item !== fn);
        },
        abort() {
            this.abortCalls++;
            events.push(['abort']);
            if (options.abortThrows) throw new Error('abort failed');
        },
        update() { this.updateCalls++; events.push(['update']); },
        swapCache() { events.push(['swapCache']); },
    };
    const storage = {
        getItem(key) {
            if (options.readThrows) throw new Error('storage unavailable');
            return Object.hasOwn(stored, key) ? stored[key] : null;
        },
        setItem(key, value) {
            if (options.writeThrows) throw new Error('storage full');
            stored[key] = String(value);
            events.push(['store', key, String(value)]);
        },
        removeItem(key) { delete stored[key]; },
    };
    const document = {
        documentElement: {
            hasAttribute: key => Object.hasOwn(attributes, key),
            getAttribute: key => attributes[key] || null,
            setAttribute: (key, value) => { attributes[key] = value; },
            removeAttribute: key => { delete attributes[key]; },
        },
        addEventListener() {}, dispatchEvent() {},
    };
    const window = {
        location, localStorage: storage,
        navigator: {onLine: options.online !== false},
        addEventListener() {}, dispatchEvent() {},
    };
    if (options.supported !== false) window.applicationCache = appCache;
    const context = {
        window, document, location, localStorage: storage,
        navigator: window.navigator, console, URL, JSON, Date,
        CustomEvent: function (name, options) { this.type = name; this.detail = options?.detail; },
        setTimeout(fn) { fn(); return 1; }, clearTimeout() {},
        setInterval() { return 1; }, clearInterval() {},
    };
    window.document = document;
    window.setTimeout = context.setTimeout;
    window.clearTimeout = context.clearTimeout;
    vm.createContext(context);
    vm.runInContext(source, context);
    assert(window.offlineCache, 'Cache controller must expose window.offlineCache');
    return {
        api: window.offlineCache, events, stored, navigations, appCache, context,
        emit(name, status, detail = {}) {
            if (status !== undefined) appCache.status = status;
            for (const fn of listeners[name] || []) fn(detail);
        },
    };
}
"""


class CacheControllerTests(unittest.TestCase):
    def run_case(self, body):
        run_node(NODE_HARNESS + "\n" + body)

    def test_default_and_legacy_preferences_do_not_opt_in(self):
        self.run_case(r"""
for (const oldValue of [undefined, true, false]) {
    const storage = oldValue === undefined ? {}
        : {dev_mode: JSON.stringify({disableAppCache: oldValue})};
    const env = boot({storage});
    assert.equal(env.api.isEnabled(), false);
    assert.equal(env.api.isReady(), false);
    assert.equal(env.navigations.length, 0);
    env.api.checkForUpdates();
    assert.equal(env.appCache.updateCalls, 0);
}
""")

    def test_enabled_online_entry_routes_once_and_preserves_url_parts(self):
        self.run_case(r"""
for (const endpoint of ['', 'index.html']) {
    const env = boot({
        storage: {offline_cache_enabled: '1'},
        url: 'https://example.test/umtx2/' + endpoint + '?example=1#settings',
    });
    assert.equal(env.navigations.length, 1);
    assert.equal(env.navigations[0],
        'https://example.test/umtx2/offline.html?example=1#settings');
}
const offline = boot({
    storage: {offline_cache_enabled: '1'},
    url: 'https://example.test/umtx2/offline.html',
    manifest: 'offline.appcache',
});
assert.equal(offline.navigations.length, 0);
""")

    def test_offline_entry_without_choice_returns_online_and_aborts(self):
        self.run_case(r"""
const env = boot({
    url: 'https://example.test/umtx2/offline.html?example=1#settings',
    manifest: 'offline.appcache', status: 3,
});
assert.equal(env.api.isEnabled(), false);
assert(env.appCache.abortCalls >= 1);
assert.deepEqual(env.navigations,
    ['https://example.test/umtx2/index.html?example=1#settings']);
assert(env.events.findIndex(x => x[0] === 'abort')
    < env.events.findIndex(x => x[0] === 'navigate'));
""")

    def test_unsupported_browser_fails_safely(self):
        self.run_case(r"""
const env = boot({supported: false});
assert.equal(env.api.isSupported(), false);
assert.equal(env.api.isReady(), false);
assert.equal(env.api.setEnabled(true), false);
assert.equal(env.navigations.length, 0);
const offline = boot({
    supported: false, storage: {offline_cache_enabled: '1'},
    url: 'https://example.test/umtx2/offline.html', manifest: 'offline.appcache',
});
assert.equal(offline.api.isReady(), false);
assert.deepEqual(offline.navigations, ['https://example.test/umtx2/index.html']);
""")

    def test_storage_failures_do_not_enable_downloads(self):
        self.run_case(r"""
const denied = boot({readThrows: true, storage: {offline_cache_enabled: '1'}});
assert.equal(denied.api.isEnabled(), false);
assert.equal(denied.navigations.length, 0);
const full = boot({writeThrows: true});
assert.equal(full.api.setEnabled(true), false);
assert.equal(full.api.isEnabled(), false);
assert.equal(full.navigations.length, 0);
assert(full.api.getState().message.length > 0);
""")

    def test_enabling_saves_choice_before_navigating(self):
        self.run_case(r"""
const env = boot();
assert.equal(env.api.setEnabled(true), true);
assert.equal(env.stored.offline_cache_enabled, '1');
assert.equal(env.navigations[0], 'https://example.test/umtx2/offline.html');
assert(env.events.findIndex(x => x[0] === 'store')
    < env.events.findIndex(x => x[0] === 'navigate'));
""")

    def test_enabling_without_connection_does_not_claim_an_offline_copy(self):
        self.run_case(r"""
const env = boot({online: false});
assert.equal(env.api.setEnabled(true), false);
assert.notEqual(env.stored.offline_cache_enabled, '1');
assert.equal(env.api.isEnabled(), false);
assert.equal(env.navigations.length, 0);
assert(env.api.getState().message.length > 0);
""")

    def test_disabling_offline_requires_connection_and_keeps_choice(self):
        self.run_case(r"""
const env = boot({
    online: false, storage: {offline_cache_enabled: '1'},
    url: 'https://example.test/umtx2/offline.html', manifest: 'offline.appcache',
    status: 1,
});
assert.equal(env.api.setEnabled(false), false);
assert.equal(env.stored.offline_cache_enabled, '1');
assert.equal(env.api.isEnabled(), true);
assert.equal(env.navigations.length, 0);
assert(env.api.getState().message.length > 0);
""")

    def test_disabling_cancels_download_and_routes_online_even_if_abort_throws(self):
        self.run_case(r"""
for (const abortThrows of [false, true]) {
    const env = boot({
        storage: {offline_cache_enabled: '1'}, abortThrows,
        url: 'https://example.test/umtx2/offline.html?test=1#settings',
        manifest: 'offline.appcache', status: 3,
    });
    assert.equal(env.api.setEnabled(false), true);
    assert.equal(env.stored.offline_cache_enabled, '0');
    assert.equal(env.api.isEnabled(), false);
    assert.equal(env.api.isReady(), false);
    assert(env.appCache.abortCalls >= 1);
    assert.deepEqual(env.navigations,
        ['https://example.test/umtx2/index.html?test=1#settings']);
}
""")

    def test_progress_alone_is_not_proof_of_a_completed_cache(self):
        self.run_case(r"""
const env = boot({
    storage: {offline_cache_enabled: '1'},
    url: 'https://example.test/umtx2/offline.html', manifest: 'offline.appcache',
});
assert.equal(env.api.isReady(), false);
env.emit('downloading', 3);
env.emit('progress', 3, {loaded: 10, total: 10, lengthComputable: true});
assert.equal(env.api.isReady(), false);
env.emit('error', 0);
assert.equal(env.api.isReady(), false);
env.emit('cached', 1);
assert.equal(env.api.isReady(), true);
env.emit('obsolete', 5);
assert.equal(env.api.isReady(), false);
""")

    def test_usable_cache_states_require_opt_in_and_offline_entry(self):
        self.run_case(r"""
for (const status of [1, 4]) {
    const enabled = boot({
        storage: {offline_cache_enabled: '1'}, status,
        url: 'https://example.test/umtx2/offline.html', manifest: 'offline.appcache',
    });
    assert.equal(enabled.api.isReady(), true);
    const disabled = boot({status});
    assert.equal(disabled.api.isReady(), false);
}
const env = boot({
    storage: {offline_cache_enabled: '1'}, status: 1,
    url: 'https://example.test/umtx2/offline.html', manifest: 'offline.appcache',
});
env.emit('checking', 2);
env.emit('error', 1);
assert.equal(env.api.isReady(), true, 'A failed update must not erase a usable old cache');
""")

    def test_update_checks_only_run_for_enabled_supported_offline_entry(self):
        self.run_case(r"""
const env = boot({
    storage: {offline_cache_enabled: '1'}, status: 1,
    url: 'https://example.test/umtx2/offline.html', manifest: 'offline.appcache',
});
env.api.checkForUpdates();
assert.equal(env.appCache.updateCalls, 1);
for (const options of [{}, {supported: false}]) {
    const inactive = boot(options);
    inactive.api.checkForUpdates();
    assert.equal(inactive.appCache.updateCalls, 0);
}
""")

    def test_subscribers_see_completed_state_and_can_unsubscribe(self):
        self.run_case(r"""
const env = boot({
    storage: {offline_cache_enabled: '1'},
    url: 'https://example.test/umtx2/offline.html', manifest: 'offline.appcache',
});
const snapshots = [];
const unsubscribe = env.api.subscribe(state => snapshots.push(state));
env.emit('progress', 3, {loaded: 1, total: 1});
assert.equal(snapshots.at(-1).ready, false);
env.emit('cached', 1);
assert.equal(snapshots.at(-1).ready, true);
assert.equal(snapshots.at(-1).enabled, true);
assert.equal(snapshots.at(-1).supported, true);
const count = snapshots.length;
unsubscribe();
env.emit('obsolete', 5);
assert.equal(snapshots.length, count);
""")


class OptionalPayloadCacheTests(unittest.TestCase):
    def test_obsolete_cache_removes_already_rendered_success_badge(self):
        run_node(NODE_HARNESS + r"""
const env = boot({
    storage: {offline_cache_enabled: '1'}, status: 1,
    url: 'https://example.test/umtx2/offline.html', manifest: 'offline.appcache',
});
class Element {
    constructor() {
        this.children = []; this.style = {}; this.className = ''; this.textContent = '';
        this.classList = {add() {}, remove() {}};
        this.parentNode = null;
    }
    get firstChild() { return this.children[0]; }
    appendChild(child) {
        this.children.push(child); child.parentNode = this; return child;
    }
    removeChild(child) {
        this.children.splice(this.children.indexOf(child), 1); child.parentNode = null;
    }
    addEventListener() {}
}
const ids = Object.fromEntries([
    'version-selection-view', 'offline-cache-toggle', 'offline-cache-status',
    'offline-cache-bookmark', 'offline-cache-update', 'offline-cache-reload',
].map(id => [id, new Element()]));
function findBadges(element) {
    return (element.className === 'version-card-cached-badge' ? [element] : [])
        .concat(...element.children.map(findBadges));
}
const document = env.context.document;
document.getElementById = id => ids[id] || null;
document.createElement = () => new Element();
document.querySelectorAll = selector => {
    assert.equal(selector, '.version-card-cached-badge');
    return findBadges(ids['version-selection-view']);
};
env.context.window.devOptions = {showPreRelease: true};
env.context.window.fw_str = '4.03';
Object.assign(env.context, {
    isPayloadVisible: () => true, getSelectedVersion: () => null,
    isFirmwareCompatible: () => true, switchPage: async () => {},
});
for (const file of ['settings-view.js', 'version-selection.js']) {
    vm.runInContext(fs.readFileSync(path.join(root,
        'document/en/ps5/js/ui', file), 'utf8'), env.context);
}
(async () => {
    await env.context.showSettingsVersionPage({
        id: 'example', displayTitle: 'Example',
        versions: [{version: '1.0', isDefault: true}],
    });
    env.context.initializeOfflineCacheSettings();
    assert.equal(findBadges(ids['version-selection-view']).length, 1);
    env.emit('obsolete', 5);
    assert.equal(env.api.isReady(), false);
    assert.equal(findBadges(ids['version-selection-view']).length, 0,
        'An open version screen must not retain a Cached badge after cache loss');
    assert.equal(ids['offline-cache-bookmark'].hidden, true);
})().catch(error => { console.error(error); process.exit(1); });
""")

    def test_settings_close_does_not_prefetch_when_cache_is_disabled(self):
        run_node(r"""
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const root = process.argv[1];
let fetches = 0;
const context = {
    window: {offlineCache: {isEnabled: () => false, isReady: () => false}},
    payload_map: [{id: 'example', versions: [{version: 'old', isDefault: false}]}],
    isPayloadVisible: () => true,
    resolveActiveVersion: () => ({version: 'old', filePath: 'payloads/example/old.elf'}),
    fetch: () => { fetches++; return Promise.resolve({}); },
    switchPage() {},
    showToast() {}, console,
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root,
    'document/en/ps5/js/ui/settings-view.js'), 'utf8'), context);
context.closeSettings();
assert.equal(fetches, 0, 'Disabled cache must not prefetch selected historical payloads');
""")

    def test_default_version_badge_requires_confirmed_offline_cache(self):
        run_node(r"""
const assert = require('node:assert/strict');
const fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const root = process.argv[1];
class Element {
    constructor() {
        this.children = []; this.style = {}; this.className = ''; this.textContent = '';
        this.classList = {add() {}, remove() {}};
    }
    get firstChild() { return this.children[0]; }
    appendChild(child) { this.children.push(child); return child; }
    removeChild(child) { this.children.splice(this.children.indexOf(child), 1); }
    addEventListener() {}
}
async function render(ready) {
    const view = new Element();
    const context = {
        window: {
            fw_str: '4.03', devOptions: {showPreRelease: true},
            offlineCache: {isReady: () => ready},
        },
        document: {getElementById: () => view, createElement: () => new Element()},
        isPayloadVisible: () => true, getSelectedVersion: () => null,
        isFirmwareCompatible: () => true, switchPage: async () => {},
    };
    vm.createContext(context);
    vm.runInContext(fs.readFileSync(path.join(root,
        'document/en/ps5/js/ui/version-selection.js'), 'utf8'), context);
    await context.showSettingsVersionPage({
        id: 'example', displayTitle: 'Example',
        versions: [
            {version: '1.0', isDefault: true},
            {version: '0.9', isDefault: false},
        ],
    });
    function badges(element) {
        return Number(element.className === 'version-card-cached-badge') +
            element.children.reduce((total, child) => total + badges(child), 0);
    }
    return badges(view);
}
(async () => {
    assert.equal(await render(false), 0, 'A default version alone is not proof of caching');
    assert.equal(await render(true), 1, 'Only the default version belongs to offline cache');
})().catch(error => { console.error(error); process.exit(1); });
""")


if __name__ == "__main__":
    unittest.main()
