import re
from typing import Dict


TIER_RULES = {
    "Tier 3": [
        r"kernel panic",
        r"hypervisor",
        r"host access",
        r"multiple users affected",
    ],
    "Tier 2": [
        r"vm freeze",
        r"lab not starting",
        r"container failed",
        r"startup.sh missing",
        r"docker error",
    ],
    "Tier 1": [
        r"login loop",
        r"cannot login",
        r"mfa reset",
        r"clear cookies",
        r"sso issue",
    ],
}


def classify_tier(question: str) -> Dict:
    q = question.lower()

    for tier, patterns in TIER_RULES.items():
        for pattern in patterns:
            if re.search(pattern, q):
                return {
                    "tier": tier,
                    "needs_escalation": tier != "Tier 0",
                }

    return {
        "tier": "Tier 0",
        "needs_escalation": False,
    }