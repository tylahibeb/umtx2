#!/usr/bin/env python3
"""Generate the opt-in offline entrypoint without caching the online entrypoint.

index.html is the maintained, manifest-free online page. offline.html is derived
from it and is the only HTML entrypoint associated with offline.appcache. The
legacy cache.appcache must stay absent so existing automatic caches can retire.
"""

import argparse
import hashlib
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
import json
import re


ONLINE_ENTRY = "index.html"
OFFLINE_ENTRY = "offline.html"
MANIFEST_NAME = "offline.appcache"
LEGACY_MANIFEST_NAME = "cache.appcache"


def calculate_file_hash(file_path):
    """Hash large payloads without loading the entire binary into memory."""
    digest = hashlib.sha256()
    with open(file_path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_default_payload_paths(directory_path):
    """Read default binary paths from metadata, not a regex over JavaScript.

    Changelog strings can contain braces, so matching generated JS object blocks
    is insufficient. Metadata contains the same maintained default version data.
    Empty filePath values belong to custom actions and need no cached binary.
    """
    root = Path(directory_path).resolve()
    default_paths = set()
    for metadata_path in sorted((root / "payloads").glob("*/metadata.json")):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ValueError(f"Cannot read payload metadata {metadata_path}: {error}") from error
        if not isinstance(metadata, dict) or not isinstance(metadata.get("versions"), list):
            raise ValueError(f"Missing versions array in {metadata_path}")
        for version in metadata["versions"]:
            if not isinstance(version, dict):
                raise ValueError(f"Invalid version entry in {metadata_path}")
            if version.get("isDefault") is not True:
                continue
            file_path = version.get("filePath", "")
            if not file_path:
                continue
            if not isinstance(file_path, str):
                raise ValueError(f"Invalid default filePath in {metadata_path}")
            relative = PurePosixPath(file_path)
            if (
                relative.is_absolute()
                or not relative.parts
                or relative.parts[0] != "payloads"
                or ".." in relative.parts
                or "\\" in file_path
            ):
                raise ValueError(f"Default payload path escapes the site: {file_path}")
            binary = root.joinpath(*relative.parts)
            if not binary.is_file() or not binary.resolve().is_relative_to(root):
                raise ValueError(f"Default payload file is missing or outside the site: {file_path}")
            default_paths.add(relative.as_posix())
    return default_paths


def extract_default_versions_from_payload_map(directory_path):
    """Compatibility alias; default paths now come from the associated metadata."""
    return extract_default_payload_paths(directory_path)


class _HtmlAttributes(HTMLParser):
    def __init__(self):
        super().__init__()
        self.attributes = []

    def handle_starttag(self, tag, attrs):
        if tag == "html":
            self.attributes = attrs


def prepare_offline_page(directory_path):
    """Create the offline copy while leaving the canonical online source intact."""
    root = Path(directory_path)
    source_path = root / ONLINE_ENTRY
    with source_path.open("r", encoding="utf-8", newline="") as source:
        online_html = source.read()
    opening = re.search(r"(<html\b)([^>]*)(>)", online_html, re.IGNORECASE)
    if opening is None:
        raise ValueError(f"No opening html element in {source_path}")
    parser = _HtmlAttributes()
    parser.feed(opening.group(0))
    if any(name == "manifest" for name, _ in parser.attributes):
        raise ValueError(
            f"{source_path} must not declare a manifest; offline caching belongs only to {OFFLINE_ENTRY}"
        )
    offline_tag = opening.group(1) + f' manifest="{MANIFEST_NAME}"' + opening.group(2) + opening.group(3)
    offline_html = online_html[:opening.start()] + offline_tag + online_html[opening.end():]
    offline_path = root / OFFLINE_ENTRY
    _write_if_changed(offline_path, offline_html)
    return offline_path


def _write_if_changed(path, contents):
    """Keep repeated generation stable, writing complete files atomically."""
    encoded = contents.encode("utf-8")
    if path.exists() and path.read_bytes() == encoded:
        return
    temporary = path.with_name("." + path.name + ".tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)


def generate_cache_manifest(directory_path, include_payloads=True):
    """Return deterministic manifest lines for the opt-in offline page.

    Never cache index.html, another HTML entrypoint, or the manifest itself.
    Doing so could associate the online page with AppCache even after its
    manifest attribute is removed. Non-default payload binaries are excluded.
    """
    root = Path(directory_path).resolve()
    default_paths = extract_default_payload_paths(root) if include_payloads else set()
    entries = []
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            continue
        if not file_path.resolve().is_relative_to(root):
            raise ValueError(f"Cache file points outside the site: {relative}")
        name = relative.as_posix()
        suffix = file_path.suffix.lower()
        if suffix in {".appcache", ".manifest", ".exe", ".py", ".pyc"}:
            continue
        if name == ONLINE_ENTRY or (suffix in {".html", ".htm"} and name != OFFLINE_ENTRY):
            continue
        if relative.parts[0] == "payloads":
            if not include_payloads:
                continue
            if suffix in {".elf", ".bin"} and name not in default_paths:
                continue
        entries.append(name + " #" + calculate_file_hash(file_path))
    return ["CACHE MANIFEST", "", *entries, "", "NETWORK:", "*"]


def generate_offline_cache(directory_path, include_payloads=True):
    """Build opt-in artifacts and retire the old automatic-cache manifest."""
    root = Path(directory_path)
    # Check default inputs before modifying any generated artifact.
    if include_payloads:
        extract_default_payload_paths(root)
    offline_path = prepare_offline_page(root)
    manifest_path = root / MANIFEST_NAME
    _write_if_changed(manifest_path, "\n".join(generate_cache_manifest(root, include_payloads)) + "\n")
    (root / LEGACY_MANIFEST_NAME).unlink(missing_ok=True)
    return offline_path, manifest_path


def clean_cache_artifacts(directory_path):
    """Remove generated/legacy caches; never add a manifest to the online page."""
    root = Path(directory_path)
    for filename in (OFFLINE_ENTRY, MANIFEST_NAME, LEGACY_MANIFEST_NAME):
        (root / filename).unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-d", "--directory-path", default=None,
        help="Site directory (defaults to the nearest index.html within three levels)"
    )
    parser.add_argument(
        "-cf", "--cloudflare-workaround", action="store_true",
        help="Compatibility option; the offline entry never aliases the online root"
    )
    parser.add_argument(
        "--update-manifest-tag", action="store_true",
        help="Deprecated compatibility option; index.html always remains manifest-free"
    )
    parser.add_argument("--clean", action="store_true", help="Remove generated and legacy offline artifacts")
    args = parser.parse_args(argv)
    if args.directory_path is None:
        candidates = []
        for depth in range(4):
            candidates = sorted(Path.cwd().glob("*/" * depth + "index.html"))
            if candidates:
                break
        if not candidates:
            parser.error("No index.html found; provide -d with the site directory")
        args.directory_path = candidates[0].parent
    root = Path(args.directory_path)
    if args.clean:
        clean_cache_artifacts(root)
        print(f"Removed offline cache artifacts from {root}; online source unchanged")
    else:
        offline_path, manifest_path = generate_offline_cache(root)
        print(f"Generated {offline_path} and {manifest_path}; online source unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
