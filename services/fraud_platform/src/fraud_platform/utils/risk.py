from __future__ import annotations


def to_risk_level(probability: float) -> str:
    if probability >= 0.8:
        return "HIGH"
    if probability >= 0.45:
        return "MEDIUM"
    return "LOW"

