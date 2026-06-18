"""
smoke_test.py — hit a running local API with no external deps.

Uses only the standard library (urllib), so `make test` works identically on
Windows cmd, Git Bash, and Linux — no curl, no shell quirks.

Usage:  python scripts/smoke_test.py [port]
"""

from __future__ import annotations
import json
import sys
import urllib.request
import urllib.error

PORT = sys.argv[1] if len(sys.argv) > 1 else "8000"
BASE = f"http://localhost:{PORT}"

HIGH_RISK = {
    "CreditScore": 600, "Geography": "Germany", "Gender": "Female", "Age": 62,
    "Tenure": 2, "Balance": 0, "NumOfProducts": 4, "HasCrCard": 1,
    "IsActiveMember": 0, "EstimatedSalary": 80000,
}


def _get(path: str):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=10) as r:
        return json.load(r)


def _post(path: str, payload: dict):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def main() -> int:
    try:
        print("health:    ", _get("/health"))
        print("prediction:", _post("/predict", HIGH_RISK))
        print("\nOK — API is responding.")
        return 0
    except urllib.error.URLError as e:
        print(f"FAILED to reach {BASE} — is the server running? ({e})")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
