import time
from collections import defaultdict

class MetricsStore:
    def __init__(self):
        self.counters = defaultdict(int)
        self.latencies = []

    def incr(self, key: str):
        self.counters[key] += 1

    def record_latency(self, ms: float):
        self.latencies.append(ms)

    def snapshot(self):
        avg_latency = (
            sum(self.latencies) / len(self.latencies)
            if self.latencies else 0
        )
        return {
            "counters": dict(self.counters),
            "avg_latency_ms": round(avg_latency, 2),
            "total_requests": self.counters.get("requests_total", 0),
        }

metrics_store = MetricsStore()