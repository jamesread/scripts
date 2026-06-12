from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib import resources
from typing import Any


def operation_to_method_name(operation: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", operation)
    return "_".join(spaced.lower().split())


@lru_cache(maxsize=1)
def load_spec() -> dict[str, Any]:
    text = resources.files("sickrock_client").joinpath("openapi.json").read_text(encoding="utf-8")
    return json.loads(text)


@lru_cache(maxsize=1)
def operations() -> dict[str, str]:
    spec = load_spec()
    mapping: dict[str, str] = {}
    for path, methods in spec["paths"].items():
        post = methods.get("post")
        if not post:
            continue
        operation = post["operationId"].split(".")[-1]
        mapping[operation_to_method_name(operation)] = operation
    return mapping


@lru_cache(maxsize=1)
def request_schemas() -> dict[str, dict[str, Any]]:
    spec = load_spec()
    schemas = spec.get("components", {}).get("schemas", {})
    result: dict[str, dict[str, Any]] = {}
    for path, methods in spec["paths"].items():
        post = methods.get("post")
        if not post:
            continue
        operation = post["operationId"].split(".")[-1]
        ref = post["requestBody"]["content"]["application/json"]["schema"].get("$ref", "")
        schema_name = ref.rsplit("/", 1)[-1]
        schema = schemas.get(schema_name, {})
        result[operation] = schema
    return result
