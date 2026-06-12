from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any

from sickrock_client._openapi import operations, request_schemas
from sickrock_client.exceptions import SickRockAPIError, SickRockCertificateError

CONNECT_PROTOCOL_VERSION = "1"
SERVICE_PREFIX = "/api/sickrock.SickRock/"


def normalize_hostname(hostname: str) -> str:
    hostname = hostname.rstrip("/")
    if not hostname.startswith(("http://", "https://")):
        hostname = f"https://{hostname}"
    return hostname


def build_ssl_context(*, verify_ssl: bool) -> ssl.SSLContext | None:
    if not verify_ssl:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
    return None


def _certificate_error_detail(exc: BaseException) -> str | None:
    cause = exc.reason if isinstance(exc, urllib.error.URLError) and exc.reason is not None else exc
    if isinstance(cause, ssl.SSLCertVerificationError):
        return str(cause)
    return None


class SickRockClient:
    """Connect RPC client for SickRock, generated from the bundled OpenAPI spec."""

    def __init__(
        self,
        base_url: str,
        token: str,
        *,
        timeout: float = 30.0,
        connect_protocol_version: str = CONNECT_PROTOCOL_VERSION,
        verify_ssl: bool = True,
    ) -> None:
        self.base_url = normalize_hostname(base_url)
        self.token = token
        self.timeout = timeout
        self.connect_protocol_version = connect_protocol_version
        self.verify_ssl = verify_ssl
        self._ssl_context = build_ssl_context(verify_ssl=verify_ssl)

    def call(self, operation: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        """Invoke a SickRock RPC by PascalCase operation name (for example ``CreateItem``)."""
        url = f"{self.base_url}{SERVICE_PREFIX}{operation}"
        payload = json.dumps(body or {}).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Connect-Protocol-Version": self.connect_protocol_version,
            },
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
                context=self._ssl_context,
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") or exc.reason
            raise SickRockAPIError(exc.code, detail, url=url) from exc
        except urllib.error.URLError as exc:
            cert_detail = _certificate_error_detail(exc)
            if cert_detail is not None:
                raise SickRockCertificateError(self.base_url, cert_detail) from exc
            raise

    def create_item(
        self,
        tc_name: str,
        additional_fields: dict[str, str] | None = None,
        *,
        sr_created: int | str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"pageId": tc_name}
        if additional_fields:
            body["additionalFields"] = additional_fields
        if sr_created is not None:
            body["srCreated"] = sr_created
        return self.call("CreateItem", body)


def _attach_operation_methods(client_cls: type[SickRockClient]) -> None:
    for method_name, operation in operations().items():
        if hasattr(client_cls, method_name):
            continue

        def _method(
            self: SickRockClient,
            body: dict[str, Any] | None = None,
            *,
            _operation: str = operation,
        ) -> dict[str, Any]:
            return self.call(_operation, body)

        _method.__name__ = method_name
        _method.__doc__ = f"Call the ``{operation}`` SickRock RPC."
        setattr(client_cls, method_name, _method)


_attach_operation_methods(SickRockClient)

OPERATIONS = operations()
REQUEST_SCHEMAS = request_schemas()
