# clean-skill

False-positive control fixture for the security scanner: every file here is
expected to score zero findings against all 25 rules in the security taxonomy.

## Layout

- `SKILL.md` — ordinary skill manifest and workflow description.
- `scripts/helper.py` — reads and writes a JSON index inside this skill folder.
- `scripts/run.sh` — lists notes and calls the Python helper.

## Design notes

- No network usage of any kind (not even harmless-looking GET requests).
- Only touches files inside its own folder; no home-directory paths.
- Plain, readable code with nothing hidden.
