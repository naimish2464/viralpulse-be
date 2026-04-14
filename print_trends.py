"""Dev helper: print first trending keywords (use trendspy; do not use filename pytrends.py)."""

import json
import sys

from core.signals.google_trends import fetch_trending_keywords

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    k = fetch_trending_keywords()
    print(json.dumps(k[:15], ensure_ascii=False, indent=2))
