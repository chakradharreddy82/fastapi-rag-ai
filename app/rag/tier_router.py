import re
from typing import Dict

TIER_RULES = {
    "Tier 3": [
        r"kernel panic",
        r"hypervisor",
        r"host access",
        r"multiple users affected",
        r"platform outage",
        r"production.*down",
        r"critical.*outage",
        r"system.*wide.*failure",
    ],

    "Tier 2": [
        r"vm.*(freeze|frozen|stuck|not responding|not working|down|failed)",
        r"(freeze|frozen|stuck).*vm",
        r"lab.*(not starting|failed|won't start|not loading|not working|down)",
        r"(lab).*failed",
        r"container.*(failed|error|not running|crash)",
        r"docker.*(error|failed|not running|crash)",
        r"time.*(sync|synchronization|wrong|skew|incorrect|drift)",
        r"clock.*(wrong|skew|incorrect)",
        r"ntp",
        r"\burgent\b",
        r"\basap\b",
        r"immediately",
        r"need help now",
        r"emergency",
    ],
    "Tier 1": [
        r"login loop",
        r"cannot login",
        r"can't login",
        r"login issue",
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