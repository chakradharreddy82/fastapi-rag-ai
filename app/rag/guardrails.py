import re
from typing import Optional, Dict

GUARDRAIL_PATTERNS = {
    "disable_logging": [
        r"disable logging",
        r"turn off logging",
        r"bypass logging",
        r"hide activity",
        r"run quietly",
    ],
    "host_access": [
        r"access hypervisor",
        r"host shell",
        r"root host",
        r"hypervisor access",
    ],
    "kernel_modification": [
        r"modify kernel",
        r"kernel parameter",
        r"load kernel module",
    ],
    "hosts_edit": [
        r"/etc/hosts",
        r"add hosts entry",
        r"edit hosts file",
    ],
    "container_edit": [
        r"edit container image",
        r"docker exec",
        r"mount startup script",
    ],
}


def detect_guardrail_violation(question: str) -> Optional[Dict]:
    q = question.lower()

    for category, patterns in GUARDRAIL_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, q):
                return {
                    "violation": True,
                    "category": category,
                }

    return None