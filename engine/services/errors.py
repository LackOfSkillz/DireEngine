class DomainError(Exception):
    pass


class ValidationError(DomainError):
    pass


class StateError(DomainError):
    pass