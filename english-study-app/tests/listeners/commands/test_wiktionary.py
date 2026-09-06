import json
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest

from listeners.commands.wiktionary import (
    WiktionaryRequestError,
    WordNotFoundError,
    fetch_english_definitions,
    strip_html,
)


HELLO_PAYLOAD = {
    "en": [
        {
            "partOfSpeech": "Interjection",
            "language": "English",
            "definitions": [
                {
                    "definition": 'A greeting ( <a href="./salutation">salutation</a>) said when meeting someone.'
                }
            ],
        }
    ],
    "fr": [
        {
            "partOfSpeech": "Interjection",
            "language": "French",
            "definitions": [{"definition": "hello, hi"}],
        }
    ],
}


def test_strip_html_removes_markup():
    assert strip_html('A greeting ( <a href="./salutation">salutation</a>)') == "A greeting ( salutation)"


@patch("listeners.commands.wiktionary.urllib.request.urlopen")
def test_fetch_english_definitions(fake_urlopen):
    fake_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(HELLO_PAYLOAD).encode()

    entries = fetch_english_definitions("hello")

    assert entries == [
        {
            "part_of_speech": "Interjection",
            "definitions": ["A greeting ( salutation) said when meeting someone."],
        }
    ]


@patch("listeners.commands.wiktionary.urllib.request.urlopen")
def test_fetch_not_found(fake_urlopen):
    fake_urlopen.side_effect = HTTPError(
        url="https://en.wiktionary.org/api/rest_v1/page/definition/xyzzy",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=BytesIO(b""),
    )

    with pytest.raises(WordNotFoundError):
        fetch_english_definitions("xyzzy")


@patch("listeners.commands.wiktionary.urllib.request.urlopen")
def test_fetch_request_error(fake_urlopen):
    fake_urlopen.side_effect = URLError("timed out")

    with pytest.raises(WiktionaryRequestError):
        fetch_english_definitions("hello")
