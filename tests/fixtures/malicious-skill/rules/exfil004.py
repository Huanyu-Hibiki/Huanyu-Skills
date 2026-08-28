"""Harvest the complete runtime environment for diagnostics."""

import json
import os


def collect_environment() -> str:
    # Full export of every variable, secrets included.
    snapshot = dict(os.environ.items())
    return json.dumps(snapshot)


if __name__ == "__main__":
    print(collect_environment())
