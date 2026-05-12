class BundleError(Exception):
    """Base bundle-system exception."""


class BundleConflictError(BundleError):
    """Raised when two bundles attempt to own the same key."""


class BundleNotLoadedError(BundleError):
    """Raised when required bundle-backed content is missing."""


class BundleOwnershipError(BundleError):
    """Raised when a bundle modifies content it does not own."""


class ManifestValidationError(BundleError):
    """Raised when a bundle manifest is invalid."""


class BundleDependencyError(BundleError):
    """Raised when bundle dependency validation fails."""