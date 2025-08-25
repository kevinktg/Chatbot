from __future__ import annotations

from typing import Dict, List


VERTICAL_REFUSALS: Dict[str, List[str]] = {
    "food": [
        "I cannot provide medical advice about allergens or intolerances. For medical guidance, consult a healthcare professional.",
        "I cannot guarantee allergen-free preparation. Please contact the venue directly for cross‑contamination controls.",
    ],
    "medical": [
        "I cannot provide medical advice, diagnosis, or treatment. For clinical guidance, contact your clinician or emergency services.",
        "I can help with appointment availability and bookings only. For prescriptions, results, or triage, please contact the clinic.",
    ],
    "trades": [
        "I cannot provide a binding quote without an on‑site inspection. I can give a non‑binding price band and schedule a visit.",
        "I cannot assess safety risks from photos alone. A licensed professional must confirm on site.",
    ],
}


def refusal_for(vertical: str) -> List[str]:
    return VERTICAL_REFUSALS.get(vertical, [])


def safety_preamble(vertical: str | None) -> str:
    if not vertical:
        return "I follow strict safety rules and avoid advice outside my scope."
    return " ".join(refusal_for(vertical))