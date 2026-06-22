from __future__ import annotations


def fetch_with_timeout(url: str, timeout: float = 5.0) -> str:
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read().decode()
    except Exception:
        return ""
