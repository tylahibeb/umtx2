#!/usr/bin/env python3
"""
Rebuild document/en/ps5/payloads.json from payloads.yaml + existing metadata.json
files — no network access, no upstream fetches.

Useful for:
  - Quickly regenerating the catalog when payload_metadata changed locally
    (e.g. a manual direct-source bump, or hand-edited metadata).
  - CI/test workflows that want to validate the catalog builder without paying
    the cost of the full update_payloads.py pipeline.

Everyday catalog generation should happen inside update_payloads.py's main();
that path also refreshes the payload binaries upstream, which this script does
not touch.
"""

import sys
from pathlib import Path

# Make update_payloads.py importable regardless of CWD.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / ".github" / "scripts"))

import yaml  # noqa: E402  (update_payloads.py imports this too)

from update_payloads import CUSTOM_CATALOG_FILE, PAYLOAD_CONFIG_FILE, generate_custom_catalog  # noqa: E402


def main() -> int:
    if not PAYLOAD_CONFIG_FILE.exists():
        print(f"Error: Config file not found: {PAYLOAD_CONFIG_FILE}", file=sys.stderr)
        return 1

    with open(PAYLOAD_CONFIG_FILE, 'r') as f:
        config = yaml.safe_load(f)

    count = generate_custom_catalog(config.get('payloads', []), CUSTOM_CATALOG_FILE)
    print(f"Done. Wrote {count} items to {CUSTOM_CATALOG_FILE.relative_to(REPO_ROOT)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
