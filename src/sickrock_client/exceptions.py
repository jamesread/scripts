class SickRockAPIError(Exception):
    """Raised when the SickRock API returns a non-success response."""

    def __init__(self, status_code: int, detail: str, *, url: str | None = None) -> None:
        self.status_code = status_code
        self.detail = detail
        self.url = url
        message = f"SickRock API HTTP {status_code}"
        if url:
            message += f" for {url}"
        message += f": {detail}"
        super().__init__(message)


class SickRockCertificateError(Exception):
    """Raised when HTTPS certificate verification fails."""

    def __init__(self, base_url: str, detail: str) -> None:
        self.base_url = base_url
        self.detail = detail
        super().__init__(
            f"HTTPS certificate verification failed for {base_url}: {detail}\n\n"
            "The server certificate could not be verified. If you trust this server, "
            "retry with -k, --no-verify-ssl, or set verify-ssl=false in your config file."
        )
