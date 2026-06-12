from __future__ import annotations

import argparse
import json
import logging
import sys

from sickrock_client.client import OPERATIONS
from sickrock_client.config import build_client, build_connection_parser, log_loaded_config_files
from sickrock_client.exceptions import SickRockAPIError, SickRockCertificateError


def _print_json(args: argparse.Namespace, data: object) -> None:
    if args.json_output:
        print(json.dumps(data, separators=(",", ":")))
    else:
        print(json.dumps(data, indent=2))


def _print_error(args: argparse.Namespace, message: str, **fields: object) -> int:
    if args.json_output:
        print(json.dumps({"error": message, **fields}), file=sys.stderr)
    else:
        print(message, file=sys.stderr)
    return 1


def _report_client_error(args: argparse.Namespace, exc: Exception) -> int:
    if isinstance(exc, SickRockAPIError):
        fields: dict[str, object] = {"status_code": exc.status_code}
        if exc.url:
            fields["url"] = exc.url
        return _print_error(args, exc.detail, **fields)
    if isinstance(exc, SickRockCertificateError):
        return _print_error(
            args,
            "certificate verification failed",
            server=exc.base_url,
            detail=exc.detail,
        )
    return _print_error(args, str(exc))


def _cmd_insert(args: argparse.Namespace) -> int:
    additional_fields = {name: value for name, value in args.field}
    if not additional_fields:
        return _print_error(args, "at least one -f FIELD VALUE is required")

    client = build_client(args)
    try:
        result = client.create_item(args.tc_name, additional_fields)
    except (SickRockAPIError, SickRockCertificateError) as exc:
        return _report_client_error(args, exc)
    _print_json(args, result)
    return 0


def _cmd_call(args: argparse.Namespace) -> int:
    operation = args.operation
    if operation not in {name for name in OPERATIONS.values()}:
        matches = [name for name in OPERATIONS.values() if name.lower() == operation.lower()]
        if len(matches) == 1:
            operation = matches[0]
        else:
            return _print_error(args, f"unknown operation: {operation}")

    if args.body is not None:
        body = json.loads(args.body)
    else:
        body = {}
        for entry in args.field:
            key, _, value = entry.partition("=")
            if not key:
                return _print_error(args, f"invalid field value: {entry}")
            body[key] = value

    client = build_client(args)
    try:
        result = client.call(operation, body)
    except (SickRockAPIError, SickRockCertificateError) as exc:
        return _report_client_error(args, exc)
    _print_json(args, result)
    return 0


def _cmd_list_operations(args: argparse.Namespace) -> int:
    if args.json_output:
        operations = [
            {"operation": operation, "method": method_name}
            for method_name, operation in sorted(OPERATIONS.items())
        ]
        _print_json(args, operations)
        return 0

    for method_name, operation in sorted(OPERATIONS.items()):
        print(f"{operation}\t{method_name}")
    return 0


_INIT_FIELDS = (
    ("version", "Version"),
    ("commit", "Commit"),
    ("date", "Build date"),
    ("dbName", "Database"),
    ("currentUsername", "User"),
)


def _cmd_info(args: argparse.Namespace) -> int:
    client = build_client(args)
    try:
        result = client.init()
    except (SickRockAPIError, SickRockCertificateError) as exc:
        return _report_client_error(args, exc)

    if args.json_output:
        _print_json(args, {"server": client.base_url, **result})
        return 0

    print(f"Server:       {client.base_url}")
    for key, label in _INIT_FIELDS:
        value = result.get(key)
        if value:
            print(f"{label + ':':<14}{value}")
    return 0


def _cmd_help(args: argparse.Namespace) -> int:
    if args.topic:
        subparser = args._subcommand_parsers.get(args.topic)
        if subparser is None:
            return _print_error(args, f"unknown command: {args.topic}")
        subparser.print_help()
        return 0
    args._root_parser.print_help()
    return 0


def build_parser() -> tuple[argparse.ArgumentParser, dict[str, argparse.ArgumentParser]]:
    parser = build_connection_parser("SickRock Connect API client")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subcommand_parsers: dict[str, argparse.ArgumentParser] = {}

    insert = subparsers.add_parser(
        "insert",
        help="insert a row into SickRock",
    )
    insert.add_argument(
        "-t",
        "--tc-name",
        dest="tc_name",
        default="default",
        help="table configuration name (default: default)",
    )
    insert.add_argument(
        "--page-id",
        dest="tc_name",
        help=argparse.SUPPRESS,
    )
    insert.add_argument(
        "-f",
        "--field",
        nargs=2,
        action="append",
        metavar=("NAME", "VALUE"),
        default=[],
        help="additional field name and value (repeatable)",
    )
    insert.set_defaults(handler=_cmd_insert)
    subcommand_parsers["insert"] = insert

    call = subparsers.add_parser("call", help="invoke any SickRock RPC operation")
    call.add_argument("operation", help="PascalCase RPC name, for example CreateItem")
    call.add_argument(
        "--body",
        help="JSON request body; overrides --field when provided",
    )
    call.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="request body field (repeatable); keys use API camelCase names",
    )
    call.set_defaults(handler=_cmd_call)
    subcommand_parsers["call"] = call

    list_ops = subparsers.add_parser(
        "list-operations",
        help="list RPC operations from the bundled OpenAPI spec",
    )
    list_ops.set_defaults(handler=_cmd_list_operations)
    subcommand_parsers["list-operations"] = list_ops

    info = subparsers.add_parser(
        "info",
        help="show SickRock server information from the Init API",
    )
    info.set_defaults(handler=_cmd_info)
    subcommand_parsers["info"] = info

    help_parser = subparsers.add_parser("help", help="show help for a command")
    help_parser.add_argument(
        "topic",
        nargs="?",
        metavar="COMMAND",
        help="command to show help for (default: top-level help)",
    )
    help_parser.set_defaults(
        handler=_cmd_help,
        _root_parser=parser,
        _subcommand_parsers=subcommand_parsers,
    )
    subcommand_parsers["help"] = help_parser

    return parser, subcommand_parsers


def main() -> None:
    parser, _ = build_parser()
    args = parser.parse_args()
    if args.json_output:
        logging.basicConfig(level=logging.ERROR)
    else:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
        log_loaded_config_files(parser)
    raise SystemExit(args.handler(args))
