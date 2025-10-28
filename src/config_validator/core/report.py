from __future__ import annotations
from collections import Counter
from typing import Any, Dict, Iterable, List
from datetime import datetime, timezone
import hashlib
import json

from ..utils.log_decorator import log_process


def utc_ts() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compute_sha256(obj: Any) -> str | None:
    if obj is None:
        return None
    try:
        payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
    except Exception:
        return None


@log_process()
def aggregate_and_summarize(results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    run_id = utc_ts()
    now_ts = run_id
    
    results_list = list(results)

    # Convert ValidationResult objects to dicts if needed
    from dataclasses import asdict
    converted_results = []
    for r in results_list:
        if hasattr(r, '__dict__') or hasattr(r, '_asdict'):
            # It's likely a dataclass or namedtuple
            converted_results.append(asdict(r))
        else:
            converted_results.append(r)
    results_list = converted_results

    valid_count = sum(1 for r in results_list if r.get("valid"))
    invalid_count = sum(1 for r in results_list if not r.get("valid"))

    registries = [r.get("registry") for r in results_list if r.get("registry")]
    counts = dict(Counter(registries))

    total_issues = sum(len(r.get("errors", [])) for r in results_list)

    # inject metadata per-file
    for r in results_list:
        r["run_id"] = run_id
        r["ts"] = now_ts
        r["valid_int"] = 1 if r.get("valid") else 0
        r["sha256"] = compute_sha256(r.get("data"))

    # Count by rule and keyword
    c_rule = Counter()
    c_kw = Counter()
    
    for r in results_list:
        for iss in r.get("issues", []):
            c_rule[iss["rule_id"]] += 1
            for k in iss.get("keywords", []):
                c_kw[k] += 1

    report: Dict[str, Any] = {
        # "summary": {
        #     "run_id": run_id,
        #     "ts": now_ts,
        #     "valid_count": valid_count,
        #     "invalid_count": invalid_count,
        #     "total_issues": total_issues,
        #     "registry_counts": counts,
        #     "counts_by_rule": dict(c_rule),
        #     "counts_by_keyword": dict(c_kw),
        # },
        "files": results_list,
        }
    return report