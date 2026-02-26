import re
from typing import Dict

TIER_RULES = {
    "Tier 3": [
        r"kernel panic",
        r"hypervisor",
        r"host access",
        r"multiple users affected",
        r"platform outage",
    ],
    "Tier 2": [
        r"vm (freeze|frozen|not responding)",
        r"lab (not starting|failed to start|won't start|not loading)",
        r"container (failed|error|not running)",
        r"startup\.sh missing",
        r"docker (error|failed|not running)",
        r"time sync",
        r"time synchronization",
        r"system time",
        r"clock (wrong|skew|incorrect)",
        r"ntp",
        r"time drift",
        r"vm time",
    ],
    "Tier 1": [
        r"login loop",
        r"cannot login",
        r"can't login",
        r"mfa reset",
        r"clear cookies",
        r"sso issue",
        r"password reset",
    ],
}


def classify_tier(question: str) -> Dict:
    q = question.lower().strip()
    priority_order = ["Tier 3", "Tier 2", "Tier 1"]

    for tier in priority_order:
        patterns = TIER_RULES.get(tier, [])
        for pattern in patterns:
            if re.search(pattern, q):
                return {
                    "tier": tier,
                    "needs_escalation": True,
                }

    return {
        "tier": "Tier 0",
        "needs_escalation": False,
    }