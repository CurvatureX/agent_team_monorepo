"""Human-in-the-loop response classifier.

Provides a simple, deterministic classifier for user responses with labels:
- approved
- rejected
- unrelated
"""

from __future__ import annotations

from typing import Dict


class HILClassifier:
    APPROVE_KEYWORDS = {"approve", "approved", "yes", "y", "ok", "sounds good", "looks good"}
    REJECT_KEYWORDS = {"reject", "rejected", "no", "n", "decline", "not approved"}

    def classify(self, text: str) -> str:
        t = (text or "").strip().lower()
        for kw in self.APPROVE_KEYWORDS:
            if kw in t:
                return "approved"
        for kw in self.REJECT_KEYWORDS:
            if kw in t:
                return "rejected"
        return "unrelated"


_svc = HILClassifier()


def get_hil_classifier() -> HILClassifier:
    return _svc


__all__ = ["HILClassifier", "get_hil_classifier"]
