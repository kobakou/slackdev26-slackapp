import json
import re
import urllib.error
import urllib.parse
import urllib.request

JISHO_SEARCH_URL = "https://jisho.org/api/v1/search/words?keyword={keyword}"
JISHO_PAGE_URL = "https://jisho.org/search/{keyword}"
USER_AGENT = "english-study-app/1.0 (Slack educational app)"
REQUEST_TIMEOUT_SECONDS = 8
MAX_ENTRIES = 5
SKIP_PARTS_OF_SPEECH = {
    "Wikipedia definition",
    "Place",
    "Product",
    "Company",
}
SKIP_TAGS = {
    "Archaic",
    "Rare term",
    "Product name",
    "Company name",
}


class JishoRequestError(Exception):
    pass


def jisho_page_url(word: str) -> str:
    return JISHO_PAGE_URL.format(keyword=urllib.parse.quote(word))


def fetch_japanese_meanings(word: str) -> list[dict]:
    payload = _get_search_payload(word)
    ranked = []
    for entry in payload.get("data", []):
        parsed = _parse_entry(word, entry)
        if parsed is not None:
            ranked.append(parsed)
    ranked.sort(key=lambda item: item["rank"])
    return [
        {
            "japanese": item["japanese"],
            "glosses": item["glosses"],
            "parts_of_speech": item["parts_of_speech"],
        }
        for item in ranked[:MAX_ENTRIES]
    ]


def _get_search_payload(word: str) -> dict:
    url = JISHO_SEARCH_URL.format(keyword=urllib.parse.quote(word))
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raise JishoRequestError(f"Jisho returned HTTP {error.code}") from error
    except urllib.error.URLError as error:
        raise JishoRequestError("Could not reach Jisho") from error

    if payload.get("meta", {}).get("status") != 200:
        raise JishoRequestError("Jisho returned an unexpected response")
    return payload


def _parse_entry(word: str, entry: dict) -> dict | None:
    if any(tag in SKIP_TAGS for tag in entry.get("tags", [])):
        return None

    glosses = []
    parts_of_speech = []
    best_rank = None
    for sense in entry.get("senses", []):
        if _should_skip_sense(sense):
            continue
        matching_ranks = []
        for gloss in sense.get("english_definitions", []):
            rank = _gloss_rank(word, gloss)
            if rank is not None:
                matching_ranks.append(rank)
        if not matching_ranks:
            continue
        glosses.extend(sense.get("english_definitions", []))
        sense_rank = min(matching_ranks)
        best_rank = sense_rank if best_rank is None else min(best_rank, sense_rank)
        for pos in sense.get("parts_of_speech", []):
            if pos and pos not in parts_of_speech and pos not in SKIP_PARTS_OF_SPEECH:
                parts_of_speech.append(pos)

    if not glosses or best_rank is None:
        return None

    japanese = _format_japanese(entry.get("japanese", []))
    if not japanese:
        return None

    if not entry.get("is_common"):
        best_rank += 0.5
    return {
        "japanese": japanese,
        "glosses": glosses[:3],
        "parts_of_speech": parts_of_speech[:2],
        "rank": best_rank,
    }


def _should_skip_sense(sense: dict) -> bool:
    if any(pos in SKIP_PARTS_OF_SPEECH for pos in sense.get("parts_of_speech", [])):
        return True
    if any(tag in SKIP_TAGS for tag in sense.get("tags", [])):
        return True
    if sense.get("source"):
        return True
    return False


def _gloss_rank(word: str, gloss: str) -> int | None:
    normalized = gloss.strip().lower()
    needle = word.strip().lower()
    if not needle or not normalized:
        return None
    if normalized == needle:
        return 0
    if normalized.startswith(f"{needle} (") or normalized.startswith(f"{needle} "):
        return 1
    if re.search(rf"\b{re.escape(needle)}\b", normalized):
        return 2 + min(len(normalized) // 12, 8)
    return None


def _format_japanese(forms: list[dict]) -> str:
    if not forms:
        return ""
    primary = forms[0]
    written = (primary.get("word") or "").strip()
    reading = (primary.get("reading") or "").strip()
    if written and reading and written != reading:
        return f"{written}（{reading}）"
    return written or reading
