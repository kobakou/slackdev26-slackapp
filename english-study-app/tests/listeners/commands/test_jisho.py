import json
from unittest.mock import patch
from urllib.error import URLError

import pytest

from listeners.commands.jisho import JishoRequestError, fetch_japanese_meanings


HELLO_PAYLOAD = {
    "meta": {"status": 200},
    "data": [
        {
            "slug": "今日は",
            "is_common": True,
            "tags": [],
            "japanese": [{"word": "今日は", "reading": "こんにちは"}],
            "senses": [
                {
                    "english_definitions": ["hello", "good day", "good afternoon"],
                    "parts_of_speech": [],
                    "tags": [],
                    "source": [],
                }
            ],
        },
        {
            "slug": "アンニョンハシムニカ",
            "is_common": False,
            "tags": [],
            "japanese": [{"reading": "アンニョンハシムニカ"}],
            "senses": [
                {
                    "english_definitions": ["hello"],
                    "parts_of_speech": [],
                    "tags": [],
                    "source": [{"language": "Korean", "word": "annyeong"}],
                }
            ],
        },
        {
            "slug": "ハローキティ",
            "is_common": False,
            "tags": [],
            "japanese": [{"reading": "ハローキティ"}],
            "senses": [
                {
                    "english_definitions": ["Hello Kitty (Sanrio product line)"],
                    "parts_of_speech": ["Noun"],
                    "tags": ["Product name"],
                    "source": [],
                }
            ],
        },
    ],
}


APPLE_PAYLOAD = {
    "meta": {"status": 200},
    "data": [
        {
            "slug": "林檎",
            "is_common": True,
            "tags": [],
            "japanese": [{"word": "林檎", "reading": "りんご"}],
            "senses": [
                {
                    "english_definitions": ["apple (fruit)"],
                    "parts_of_speech": ["Noun"],
                    "tags": [],
                    "source": [],
                },
                {
                    "english_definitions": ["Apple"],
                    "parts_of_speech": ["Wikipedia definition"],
                    "tags": [],
                    "source": [],
                },
            ],
        },
        {
            "slug": "梨",
            "is_common": True,
            "tags": [],
            "japanese": [{"word": "梨", "reading": "なし"}],
            "senses": [
                {
                    "english_definitions": ["nashi", "Japanese pear", "Asian pear"],
                    "parts_of_speech": ["Noun"],
                    "tags": [],
                    "source": [],
                }
            ],
        },
        {
            "slug": "林檎-2",
            "is_common": False,
            "tags": [],
            "japanese": [{"word": "林檎", "reading": "りゅうごう"}],
            "senses": [
                {
                    "english_definitions": ["apple"],
                    "parts_of_speech": ["Noun"],
                    "tags": ["Archaic"],
                    "source": [],
                }
            ],
        },
    ],
}


@patch("listeners.commands.jisho.urllib.request.urlopen")
def test_fetch_japanese_meanings_filters_noise(fake_urlopen):
    fake_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(HELLO_PAYLOAD).encode()

    entries = fetch_japanese_meanings("hello")

    assert entries == [
        {
            "japanese": "今日は（こんにちは）",
            "glosses": ["hello", "good day", "good afternoon"],
            "parts_of_speech": [],
        }
    ]


@patch("listeners.commands.jisho.urllib.request.urlopen")
def test_fetch_japanese_meanings_requires_matching_gloss(fake_urlopen):
    fake_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(APPLE_PAYLOAD).encode()

    entries = fetch_japanese_meanings("apple")

    assert [entry["japanese"] for entry in entries] == ["林檎（りんご）"]
    assert entries[0]["glosses"] == ["apple (fruit)"]
    assert entries[0]["parts_of_speech"] == ["Noun"]


@patch("listeners.commands.jisho.urllib.request.urlopen")
def test_fetch_japanese_meanings_empty(fake_urlopen):
    fake_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(
        {"meta": {"status": 200}, "data": []}
    ).encode()

    assert fetch_japanese_meanings("xyzzy") == []


@patch("listeners.commands.jisho.urllib.request.urlopen")
def test_fetch_japanese_meanings_request_error(fake_urlopen):
    fake_urlopen.side_effect = URLError("timed out")

    with pytest.raises(JishoRequestError):
        fetch_japanese_meanings("hello")
