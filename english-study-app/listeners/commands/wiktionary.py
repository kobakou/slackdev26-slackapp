import json
import re
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

WIKTIONARY_DEFINITION_URL = "https://en.wiktionary.org/api/rest_v1/page/definition/{term}"
WIKTIONARY_PAGE_URL = "https://en.wiktionary.org/wiki/{term}"
USER_AGENT = "english-study-app/1.0 (Slack educational app)"
REQUEST_TIMEOUT_SECONDS = 8
MAX_PARTS_OF_SPEECH = 4
MAX_DEFINITIONS_PER_POS = 5


class WordNotFoundError(Exception):
    def __init__(self, word: str):
        super().__init__(word)
        self.word = word


class WiktionaryRequestError(Exception):
    pass


class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        self._chunks.append(data)

    def text(self) -> str:
        return "".join(self._chunks)


def strip_html(value: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(value)
    parser.close()
    return re.sub(r"\s+", " ", parser.text()).strip()


def wiktionary_page_url(word: str) -> str:
    return WIKTIONARY_PAGE_URL.format(term=urllib.parse.quote(word.replace(" ", "_"), safe=""))


def fetch_english_definitions(word: str) -> list[dict]:
    payload = _get_definition_payload(word)
    if payload is None and word != word.lower():
        payload = _get_definition_payload(word.lower())
    if payload is None:
        raise WordNotFoundError(word)

    entries = []
    for group in payload.get("en", []):
        definitions = []
        for item in group.get("definitions", []):
            definition = strip_html(item.get("definition", ""))
            if definition:
                definitions.append(definition)
            if len(definitions) >= MAX_DEFINITIONS_PER_POS:
                break
        if not definitions:
            continue
        entries.append(
            {
                "part_of_speech": group.get("partOfSpeech") or "Definition",
                "definitions": definitions,
            }
        )
        if len(entries) >= MAX_PARTS_OF_SPEECH:
            break

    if not entries:
        raise WordNotFoundError(word)
    return entries


def _get_definition_payload(term: str) -> dict | None:
    encoded = urllib.parse.quote(term.replace(" ", "_"), safe="")
    url = WIKTIONARY_DEFINITION_URL.format(term=encoded)
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise WiktionaryRequestError(f"Wiktionary returned HTTP {error.code}") from error
    except urllib.error.URLError as error:
        raise WiktionaryRequestError("Could not reach Wiktionary") from error
