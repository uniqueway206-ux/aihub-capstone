class AIHubError(Exception):
    """Base class; `status` maps to the HTTP status returned by the API."""

    status = 500


class ConfigError(AIHubError):
    status = 503


class ValidationError(AIHubError):
    status = 400


class UnsafeSQLError(ValidationError):
    pass


class UnsafeURLError(ValidationError):
    pass


class UpstreamError(AIHubError):
    status = 502
