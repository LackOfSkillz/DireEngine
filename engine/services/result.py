from dataclasses import dataclass, field


@dataclass(slots=True)
class ActionResult:
    success: bool
    data: dict = field(default_factory=dict)
    messages: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    @classmethod
    def ok(cls, data=None, messages=None):
        return cls(success=True, data=dict(data or {}), messages=list(messages or []), errors=[])

    @classmethod
    def fail(cls, errors=None, messages=None, data=None):
        return cls(success=False, data=dict(data or {}), messages=list(messages or []), errors=list(errors or []))

    @property
    def amount(self):
        return float(self.data.get("amount", 0.0) or 0.0)

    @property
    def band(self):
        return str(self.data.get("band", "") or "")

    @property
    def hit(self):
        return bool(self.data.get("hit", False))

    @property
    def damage(self):
        return int(self.data.get("damage", 0) or 0)

    @property
    def roundtime(self):
        return float(self.data.get("roundtime", 0.0) or 0.0)

    @property
    def details(self):
        return dict(self.data.get("details", {}) or {})