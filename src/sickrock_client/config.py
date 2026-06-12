from __future__ import annotations

import json
import logging
import sys

import configargparse

DEFAULT_SETTINGS = "/etc/SickRockClient/settings.env"
logger = logging.getLogger(__name__)


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {value!r}")


def add_connection_args(parser: configargparse.ArgParser) -> None:
    parser.add(
        "-c",
        "--config",
        is_config_file=True,
        help=f"settings file (default: {DEFAULT_SETTINGS})",
    )
    parser.add(
        "--hostname",
        dest="hostname",
        help="SickRock base URL (config: hostname or SICKROCK_URL; env: SICKROCK_URL)",
    )
    parser.add(
        "--SICKROCK_URL",
        dest="hostname",
        env_var="SICKROCK_URL",
        help="SickRock base URL (alias for --hostname; env: SICKROCK_URL)",
    )
    parser.add(
        "--bearer-token",
        dest="bearer_token",
        env_var="BEARER_TOKEN",
        help="SickRock API key (config: bearer-token or BEARER_TOKEN; env: BEARER_TOKEN)",
    )
    parser.add(
        "--BEARER_TOKEN",
        dest="bearer_token",
        help=configargparse.SUPPRESS,
    )
    parser.add(
        "--verify-ssl",
        dest="verify_ssl",
        type=parse_bool,
        default=True,
        env_var="VERIFY_SSL",
        help="verify HTTPS server certificates (default: true; config: verify-ssl; env: VERIFY_SSL)",
    )
    parser.add(
        "-k",
        "--no-verify-ssl",
        dest="verify_ssl",
        action="store_const",
        const=False,
        help="disable HTTPS certificate verification",
    )
    parser.add(
        "-j",
        "--json",
        dest="json_output",
        action="store_true",
        help="output JSON only and suppress informational messages",
    )


def build_connection_parser(description: str) -> configargparse.ArgParser:
    parser = configargparse.ArgParser(
        description=description,
        default_config_files=[DEFAULT_SETTINGS],
        ignore_unknown_config_file_keys=True,
    )
    add_connection_args(parser)
    return parser


def loaded_config_files(parser: configargparse.ArgParser) -> list[str]:
    sources = parser.get_source_to_settings_dict()
    return [
        source.split("|", 1)[1]
        for source in sources
        if source.startswith("config_file|")
    ]


def log_loaded_config_files(parser: configargparse.ArgParser) -> None:
    for path in loaded_config_files(parser):
        logger.info("loaded config file: %s", path)


def require_connection(args: configargparse.Namespace) -> tuple[str, str]:
    if not args.hostname:
        _connection_error(
            args,
            "hostname is required (config: hostname or SICKROCK_URL; env: SICKROCK_URL)",
        )
    if not args.bearer_token:
        _connection_error(
            args,
            "bearer-token is required (config: bearer-token or BEARER_TOKEN; env: BEARER_TOKEN)",
        )
    return args.hostname, args.bearer_token


def _connection_error(args: configargparse.Namespace, message: str) -> None:
    if getattr(args, "json_output", False):
        print(json.dumps({"error": message}), file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(message)


def build_client(args: configargparse.Namespace):
    from sickrock_client.client import SickRockClient

    hostname, token = require_connection(args)
    return SickRockClient(hostname, token, verify_ssl=args.verify_ssl)
