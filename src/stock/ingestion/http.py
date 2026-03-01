from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def get_text(url: str, params: dict | None = None, timeout: int = 20, headers: dict | None = None) -> str:
    full_url = url if not params else f"{url}?{urlencode(params)}"
    merged_headers = {"User-Agent": "Mozilla/5.0"}
    if headers:
        merged_headers.update(headers)

    last_err: Exception | None = None
    for attempt in range(3):
        try:
            req = Request(full_url, headers=merged_headers)
            with urlopen(req, timeout=timeout) as resp:
                data = resp.read()
            return data.decode("utf-8", errors="replace")
        except HTTPError as e:
            last_err = e
            if e.code in (429, 503):
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
        except URLError as e:
            last_err = e
            time.sleep(0.8 * (attempt + 1))
            continue

    if last_err:
        raise last_err
    raise RuntimeError("HTTP 请求失败")


def get_json(url: str, params: dict | None = None, timeout: int = 20, headers: dict | None = None) -> dict:
    text = get_text(url=url, params=params, timeout=timeout, headers=headers)
    return json.loads(text)
