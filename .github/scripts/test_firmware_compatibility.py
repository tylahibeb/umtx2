#!/usr/bin/env python3
"""Offline regressions for configured firmware rules and browser filtering."""

import ast
import base64
from copy import deepcopy
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from typing import Dict, List, Optional
from unittest.mock import Mock


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_updater_functions(names, overrides=None):
    """Exercise real helpers without importing network/install side effects."""
    source = REPO_ROOT / ".github/scripts/update_payloads.py"
    tree = ast.parse(source.read_text(), filename=str(source))
    functions = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in names
    ]
    if {node.name for node in functions} != set(names):
        raise AssertionError("Requested updater helper is missing")
    namespace = {
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "Path": Path,
        "fnmatch": fnmatch,
        "re": re,
        "json": json,
    }
    namespace.update(overrides or {})
    module = ast.Module(body=functions, type_ignores=[])
    exec(compile(module, str(source), "exec"), namespace)
    return namespace


def load_detector(mock_subprocess):
    return load_updater_functions(
        ["detect_firmware_compatibility"], {"subprocess": mock_subprocess}
    )["detect_firmware_compatibility"]


class ConfiguredFirmwareTests(unittest.TestCase):
    def setUp(self):
        self.processes = Mock()
        self.detect = load_detector(self.processes)

    def test_explicit_empty_rules_do_not_scrape_ps5upload_readme(self):
        # The old parser misread 13.60 as 3.60 and dropped every 4.xx console.
        readme = "PS5 firmware: 1.00 through 13.60. Tested on 5.10."
        self.processes.run.side_effect = [
            subprocess.CompletedProcess([], 0, '{"repositoryTopics": []}'),
            subprocess.CompletedProcess(
                [], 0, base64.b64encode(readme.encode()).decode()
            ),
        ]
        self.assertEqual(self.detect("phantomptr/ps5upload", []), [])
        self.processes.run.assert_not_called()

    def test_explicit_rules_survive_without_network_lookup(self):
        rules = ["3.", "4.03", "5.50", "7.01.01", "12."]
        self.assertEqual(self.detect("example/payload", rules), rules)
        self.processes.run.assert_not_called()

    def test_missing_rules_do_not_infer_restrictions(self):
        self.assertEqual(self.detect("example/payload", None), [])
        self.processes.run.assert_not_called()

    def test_invalid_rules_fail_instead_of_silently_hiding_payloads(self):
        invalid = [
            "4.03", ("4.03",), {}, 4,
            [None], [4.03], [""], ["4"], ["4.0"], ["4.030"],
            ["4.xx"], ["4.03-5.50"], [" 4.03"], ["4.03\n"],
        ]
        for rules in invalid:
            with self.subTest(rules=rules):
                with self.assertRaises(ValueError):
                    self.detect("example/payload", rules)
        self.processes.run.assert_not_called()

    def test_yaml_rules_agree_with_every_metadata_file(self):
        import yaml

        config = yaml.safe_load((REPO_ROOT / ".github/payloads.yaml").read_text())
        payloads = config["payloads"]
        ids = [payload["id"] for payload in payloads]
        self.assertGreaterEqual(len(ids), 40)
        self.assertEqual(len(ids), len(set(ids)), "Payload IDs must be unique")
        metadata_files = {
            path.parent.name: path
            for path in (REPO_ROOT / "document/en/ps5/payloads").glob("*/metadata.json")
        }
        self.assertEqual(set(ids), set(metadata_files),
                         "The firmware audit must cover every configured and on-disk payload")
        for payload in payloads:
            with self.subTest(payload=payload["id"]):
                metadata = json.loads(metadata_files[payload["id"]].read_text())
                self.assertEqual(payload.get("supportedFirmwares", []),
                                 metadata.get("supportedFirmwares", []),
                                 "Regenerate metadata after changing YAML firmware rules")


class ReleaseSelectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.releases = Mock()
        self.details = Mock()
        self.process = Mock(side_effect=self.make_version)
        self.helpers = load_updater_functions(
            ["update_payload_from_github_release", "match_asset", "match_zip_asset",
             "_finalize_versions"],
            {"get_github_releases": self.releases,
             "get_release_details": self.details,
             "_process_release_version": self.process,
             "MAX_VERSIONS_PER_PAYLOAD": 999,
             "PAYLOADS_DIR": self.root},
        )
        self.update = self.helpers["update_payload_from_github_release"]
        self.config = {"id": "payload", "sourceRepo": "example/payload",
                       "sourcePattern": "payload*.elf"}

    @staticmethod
    def make_version(payload_id, version, filename, url, body, published_at,
                     is_prerelease, existing, fail_reason=""):
        if fail_reason:
            return existing.get(version)
        return {"version": version, "fileName": filename,
                "releaseDate": published_at[:10], "isDefault": False,
                "isPreRelease": is_prerelease}

    @staticmethod
    def release_details(filename, published_at="2026-10-01"):
        return {"assets": [{"name": filename, "url": "https://example.com/" + filename}],
                "body": "", "publishedAt": published_at}

    def test_opt_out_skips_prerelease_fetch_and_orphan_preservation(self):
        self.releases.return_value = [
            {"tagName": "v2-test", "isPrerelease": True},
            {"tagName": "v1", "isPrerelease": False},
        ]
        self.details.return_value = self.release_details("payload.elf")
        # A downloaded experimental binary must not return through orphan fallback.
        old_directory = self.root / "payload" / "2-test"
        old_directory.mkdir(parents=True)
        (old_directory / "experimental.elf").write_bytes(b"experimental")
        metadata = {"versions": [{"version": "2-test", "fileName": "experimental.elf",
                                  "isPreRelease": True, "releaseDate": "2026-10-02"}]}
        result = self.update(dict(self.config, includePrereleases=False), metadata)
        self.details.assert_called_once_with("example/payload", "v1")
        self.assertEqual([v["version"] for v in result], ["1"])
        self.assertTrue(result[0]["isDefault"])
        self.assertEqual(self.process.call_args.args[7], {})

    def test_excluded_firmware_variants_cannot_win_asset_selection(self):
        self.releases.return_value = [{"tagName": "v1", "isPrerelease": False}]
        self.details.return_value = {
            "publishedAt": "2026-10-01", "body": "",
            "assets": [{"name": name, "url": "https://example.com/" + name} for name in
                       ["payload-fw13.elf", "payload-mtk-test.elf", "payload.elf"]],
        }
        result = self.update(
            dict(self.config, sourceExcludePatterns=["*-fw*.elf", "*-mtk-test.elf"]),
            {"versions": []},
        )
        self.assertEqual(result[0]["fileName"], "payload.elf")
        self.assertEqual(self.process.call_args.args[3], "https://example.com/payload.elf")

    def test_default_policy_still_includes_prereleases(self):
        self.releases.return_value = [
            {"tagName": "v2-test", "isPrerelease": True},
            {"tagName": "v1", "isPrerelease": False},
        ]
        self.details.side_effect = [
            self.release_details("payload-test.elf", "2026-10-02"),
            self.release_details("payload.elf", "2026-10-01"),
        ]
        result = self.update(self.config, {"versions": []})
        self.assertEqual(self.details.call_count, 2)
        self.assertEqual([v["version"] for v in result], ["2-test", "1"])
        self.assertTrue(result[0]["isDefault"])
        self.assertTrue(result[0]["isPreRelease"])

    def test_stable_fallback_gets_default_after_beta_is_removed(self):
        self.releases.return_value = []
        metadata = {"versions": [
            {"version": "2-beta", "fileName": "payload-beta.elf",
             "releaseDate": "2026-10-02", "isPreRelease": True, "isDefault": True},
            {"version": "1", "fileName": "payload.elf",
             "releaseDate": "2026-10-01", "isPreRelease": False, "isDefault": False},
        ]}
        result = self.update(dict(self.config, includePrereleases=False), metadata)
        self.assertEqual([version["version"] for version in result], ["1"])
        self.assertTrue(result[0]["isDefault"],
                        "The stable fallback needs a default for UI selection and AppCache")
        self.details.assert_not_called()
        self.process.assert_not_called()

    def test_excluded_existing_variants_do_not_return_on_upstream_failure(self):
        self.releases.return_value = [{"tagName": "v1", "isPrerelease": False}]
        self.details.return_value = self.release_details("payload-fw13.elf")
        existing = [
            {"version": "1", "fileName": "payload-fw13.elf", "releaseDate": "2026-10-01"},
            {"version": "0", "fileName": "payload-mtk-test.elf", "releaseDate": "2026-09-01"},
        ]
        for version in existing:
            directory = self.root / "payload" / version["version"]
            directory.mkdir(parents=True)
            (directory / version["fileName"]).write_bytes(b"unsupported variant")
        result = self.update(
            dict(self.config, sourceExcludePatterns=["*-fw*.elf", "*-mtk-test.elf"]),
            {"versions": existing},
        )
        self.assertEqual(result, [],
                         "Excluded metadata must not return via failed-asset or orphan fallback")
        self.assertEqual(self.process.call_args.args[7], {})


class DirectSourceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.download = Mock(side_effect=AssertionError("A local-only payload must not download"))
        self.helpers = load_updater_functions(
            ["update_payload_from_direct", "_finalize_versions", "calculate_file_hash"],
            {"PAYLOADS_DIR": self.root, "hashlib": hashlib, "download_file": self.download},
        )
        self.update = self.helpers["update_payload_from_direct"]
        self.binary = b"\x7fELF" + b"\x00" * 64

    def write_binary(self, version, name="local.elf"):
        directory = self.root / "local-payload" / version
        directory.mkdir(parents=True)
        binary_path = directory / name
        binary_path.write_bytes(self.binary)
        return binary_path

    def test_unreleased_local_binary_preserves_prerelease_and_manual_default(self):
        binary_path = self.write_binary("unreleased")
        config = {"id": "local-payload", "manualVersions": [
            {"version": "unreleased", "fileName": "local.elf", "url": "",
             "isPreRelease": True, "isDefault": True},
        ]}
        versions = self.update(config, {"versions": []})
        self.assertEqual(len(versions), 1)
        version = versions[0]
        self.assertEqual(version["version"], "unreleased")
        self.assertEqual(version["releaseDate"], "")
        self.assertEqual(version["downloadUrl"], "")
        self.assertTrue(version["isPreRelease"])
        self.assertTrue(version["isDefault"],
                        "A dateless local build needs its explicit default for offline caching")
        self.assertEqual(version["filePath"], "payloads/local-payload/unreleased/local.elf")
        self.assertEqual(version["hash"], hashlib.sha256(self.binary).hexdigest())
        self.assertEqual(version["fileSize"], len(self.binary))
        self.assertEqual(binary_path.read_bytes(), self.binary)
        self.download.assert_not_called()

    def test_dated_versions_keep_newest_date_default_despite_stale_manual_flag(self):
        self.write_binary("old")
        self.write_binary("new")
        config = {"id": "local-payload", "manualVersions": [
            {"version": "old", "fileName": "local.elf", "url": "",
             "releaseDate": "2026-09-01", "isDefault": True},
            {"version": "new", "fileName": "local.elf", "url": "",
             "releaseDate": "2026-10-01", "isDefault": False},
        ]}
        versions = self.update(config, {"versions": []})
        self.assertEqual([v["version"] for v in versions if v["isDefault"]], ["new"])
        self.download.assert_not_called()

    def test_missing_local_binary_with_empty_url_does_not_invent_a_version(self):
        config = {"id": "local-payload", "manualVersions": [
            {"version": "missing", "fileName": "local.elf", "url": "",
             "isPreRelease": True, "isDefault": True},
        ]}
        self.assertEqual(self.update(config, {"versions": []}), [])
        self.assertFalse((self.root / "local-payload/missing/local.elf").exists())
        self.download.assert_not_called()


class OfflineRefreshTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.payloads = self.root / "payloads"
        self.payloads.mkdir()
        self.map_file = self.root / "payload_map.js"
        self.map_file.write_text("original map")
        self.catalog_file = self.root / "payloads.json"
        self.catalog_file.write_text("original catalog")
        self.processes = Mock()
        self.network = Mock(side_effect=AssertionError("Offline rebuild used network"))
        self.generate_map = Mock(return_value="rebuilt map")
        self.generate_catalog = Mock()
        self.helpers = load_updater_functions(
            ["refresh_firmware_compatibility", "detect_firmware_compatibility",
             "load_metadata", "save_metadata"],
            {"PAYLOADS_DIR": self.payloads, "PAYLOAD_MAP_FILE": self.map_file,
             "CUSTOM_CATALOG_FILE": self.catalog_file,
             "subprocess": self.processes,
             "json_serial": str,
             "get_github_releases": self.network, "download_file": self.network,
             "detect_license": self.network,
             "generate_payload_map_js": self.generate_map,
             "generate_custom_catalog": self.generate_catalog},
        )
        self.refresh = self.helpers["refresh_firmware_compatibility"]

    def write_metadata(self, payload_id="payload"):
        directory = self.payloads / payload_id
        directory.mkdir()
        metadata = {"id": payload_id, "license": {"type": "MIT"},
                    "supportedFirmwares": ["3."],
                    "versions": [{"version": "1", "fileName": "payload.elf",
                                  "hash": "a" * 64, "isDefault": True,
                                  "changelog": ["Preserve release notes"]}]}
        metadata_file = directory / "metadata.json"
        metadata_file.write_text(json.dumps(metadata))
        return metadata_file, metadata

    def test_rebuild_changes_only_compatibility_without_network(self):
        metadata_file, original = self.write_metadata()
        config = [{"id": "payload", "supportedFirmwares": []}]
        original_config = deepcopy(config)
        self.refresh(config)
        actual = json.loads(metadata_file.read_text())
        expected = dict(original, supportedFirmwares=[])
        self.assertEqual(actual, expected)
        self.assertEqual(config, original_config)
        processed = self.generate_map.call_args.args[0]
        self.assertEqual(processed[0]["versions"], original["versions"])
        self.assertEqual(self.map_file.read_text(), "rebuilt map")
        self.network.assert_not_called()
        self.processes.run.assert_not_called()

    def test_missing_metadata_aborts_before_any_writes(self):
        metadata_file, _ = self.write_metadata()
        original_bytes = metadata_file.read_bytes()
        config = [{"id": "payload", "supportedFirmwares": []},
                  {"id": "missing", "supportedFirmwares": []}]
        with self.assertRaises(ValueError):
            self.refresh(config)
        self.assertEqual(metadata_file.read_bytes(), original_bytes)
        self.assertEqual(self.map_file.read_text(), "original map")
        self.assertEqual(self.catalog_file.read_text(), "original catalog")
        self.generate_map.assert_not_called()
        self.generate_catalog.assert_not_called()


class BrowserFirmwareTests(unittest.TestCase):
    def test_actual_browser_filter(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node.js is required for firmware regressions")
        script = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const context = { window: { devOptions: {}, fw_str: '4.03' } };
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), context);
const compatible = context.window.isFirmwareCompatible;
let checked = 0;
function check(rules, firmware, expected) {
    context.window.fw_str = firmware;
    const payload = rules === undefined ? {} : { supportedFirmwares: rules };
    assert.equal(compatible(payload), expected,
        JSON.stringify({rules, firmware, expected}));
    checked++;
}
// An unrestricted payload must be visible throughout the host's firmware range.
for (const firmware of ['1.00', '2.50', '3.20', '4.03', '4.50', '5.50']) {
    check([], firmware, true);
}
check(undefined, '4.03', true);
// Major prefixes must not accidentally match another major version.
check(['3.'], '3.20', true);
check(['3.'], '13.20', false);
check(['4.'], '4.50', true);
check(['4.'], '5.00', false);
// Full versions describe a single firmware, not an arbitrary text prefix.
check(['4.03'], '4.03', true);
check(['4.03'], '4.030', false);
check(['4.03'], '4.50', false);
check(['4.03', '5.50'], '5.50', true);
check(['7.01.01'], '7.01.01', true);
check(['7.01.01'], '7.01', false);
check(['7.01.01'], '7.01.010', false);
check(['4.03'], '', false);
context.window.devOptions.bypassFirmware = true;
check(['4.03'], '5.00', true);
console.log(`Browser firmware regressions passed (${checked} cases)`);
"""
        result = subprocess.run(
            [node, "-e", script,
             str(REPO_ROOT / "document/en/ps5/js/utils/firmware-compat.js")],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_generated_map_matches_metadata_and_audited_rules(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node.js is required for firmware regressions")
        script = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = process.argv[1];
const context = { window: { devOptions: {} } };
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root, 'document/en/ps5/payload_map.js'), 'utf8'), context);
vm.runInContext(fs.readFileSync(path.join(root,
    'document/en/ps5/js/utils/firmware-compat.js'), 'utf8'), context);
const payloads = JSON.parse(vm.runInContext('JSON.stringify(payload_map)', context));
assert.ok(payloads.length >= 40, 'The audit must cover the complete payload set');
for (const payload of payloads) {
    const metadata = JSON.parse(fs.readFileSync(path.join(root,
        'document/en/ps5/payloads', payload.id, 'metadata.json'), 'utf8'));
    assert.deepEqual(payload.supportedFirmwares || [], metadata.supportedFirmwares || [],
        `${payload.id}: generated map and metadata firmware rules differ`);
}
function check(id, firmware, expected) {
    const payload = payloads.find(p => p.id === id);
    assert.ok(payload, `Audited payload ${id} must exist`);
    context.window.fw_str = firmware;
    assert.equal(context.window.isFirmwareCompatible(payload), expected,
        JSON.stringify({id, firmware, expected}));
}
check('ps5upload', '4.03', true);
check('hearbridge', '4.03', true);
check('kylin-core', '4.00', false);
check('kylin-core', '4.02', false);
check('kylin-core', '4.03', true);
check('ps5debug-ng', '1.00', false);
check('ps5debug-ng', '2.50', false);
check('ps5debug-ng', '4.03', true);
check('etahen', '1.00', true);
check('etahen', '2.50', true);
console.log(`Firmware metadata agrees for all ${payloads.length} payloads`);
"""
        result = subprocess.run(
            [node, "-e", script, str(REPO_ROOT)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_refresh_detects_firmware_only_updates(self):
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node.js is required for firmware regressions")
        script = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = process.argv[1];
const mapText = fs.readFileSync(path.join(root, 'document/en/ps5/payload_map.js'), 'utf8');
const settingsText = fs.readFileSync(path.join(root,
    'document/en/ps5/js/ui/settings-view.js'), 'utf8');
function fingerprints(text) {
    const context = { window: {} };
    vm.createContext(context);
    vm.runInContext(text, context);
    vm.runInContext(settingsText, context);
    return {
        local: context.generatePayloadFingerprint(),
        remote: context.extractFingerprintFromText(text)
    };
}
const original = fingerprints(mapText);
assert.equal(original.local, original.remote,
    'Refresh must recognize the current generated map as unchanged');

// Change just PS5 Upload's firmware rule, preserving every binary/version/hash.
const start = mapText.indexOf('id: "ps5upload",');
assert.notEqual(start, -1, 'The PS5 Upload regression fixture must exist');
let end = mapText.indexOf('\n        id: "', start + 1);
if (end === -1) end = mapText.length;
const block = mapText.slice(start, end)
    .replace(/supportedFirmwares:\s*\[[^\]]*\],?/g, '')
    .replace('id: "ps5upload",', 'id: "ps5upload",\n        supportedFirmwares: ["99."],');
const changedText = mapText.slice(0, start) + block + mapText.slice(end);
const changed = fingerprints(changedText);
assert.equal(changed.local, changed.remote,
    'In-memory and downloaded firmware rules must use the same fingerprint');
assert.notEqual(original.local, changed.remote,
    'Changing only compatibility must trigger the update notice');
const withoutFirmware = value => JSON.parse(value).map(({id, versions}) => ({id, versions}));
assert.deepEqual(withoutFirmware(original.local), withoutFirmware(changed.local),
    'The regression must not rely on changes to versions or hashes');
"""
        result = subprocess.run(
            [node, "-e", script, str(REPO_ROOT)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
