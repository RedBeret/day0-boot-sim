class Day0BootSimError(Exception):
    """Base exception for the simulator."""


class RetryableGatewayError(Day0BootSimError):
    """A temporary upstream failure that can be retried."""


class NonRetryableGatewayError(Day0BootSimError):
    """A permanent upstream failure."""


class ResourceMissingError(NonRetryableGatewayError):
    """A requested synthetic resource was not found."""
