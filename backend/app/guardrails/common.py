from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailResult:
    action: str
    reason: str = ""
    message: str = ""