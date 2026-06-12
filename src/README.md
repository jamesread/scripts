# sickrock_client

Python client and CLI for the [SickRock](https://github.com/jamesread/SickRock) Connect API.

## Install

```bash
pip install sickrock_client
```

## CLI

The package installs a `src` command:

```bash
src info
src -j info
src insert -t default -f type TASK -f timestamp "2026-06-12 12:00:00"
src call Init
src list-operations
src help insert
```

Configuration defaults to `/etc/SickRockClient/settings.env` and supports `SICKROCK_URL`, `BEARER_TOKEN`, and `VERIFY_SSL` (or `verify-ssl=false` in the config file). Use `-k` or `--no-verify-ssl` to skip certificate verification. Use `-j` or `--json` for JSON-only output.

## Library

```python
from sickrock_client import SickRockClient

client = SickRockClient("https://example.com", "token")
item = client.create_item("default", {"type": "TASK", "timestamp": "2026-06-12 12:00:00"})
info = client.init()
```
