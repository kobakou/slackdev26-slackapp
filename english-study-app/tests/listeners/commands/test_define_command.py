import logging
from unittest.mock import Mock, patch

from slack_bolt import Ack, Respond

from listeners.commands.define_command import define_command_callback
from listeners.commands.jisho import JishoRequestError
from listeners.commands.wiktionary import WiktionaryRequestError, WordNotFoundError

test_logger = logging.getLogger(__name__)


class TestDefineCommand:
    def setup_method(self):
        self.fake_ack = Mock(Ack)
        self.fake_respond = Mock(Respond)

    def test_usage_when_word_missing(self):
        define_command_callback(
            {"text": "  "},
            ack=self.fake_ack,
            respond=self.fake_respond,
            logger=test_logger,
        )

        self.fake_ack.assert_called_once()
        self.fake_respond.assert_called_once()
        assert self.fake_respond.call_args.args[0] == "Usage: `/define <english word>`"

    @patch("listeners.commands.define_command.fetch_japanese_meanings")
    @patch("listeners.commands.define_command.fetch_english_definitions")
    def test_responds_with_english_and_japanese(self, fake_english, fake_japanese):
        fake_english.return_value = [
            {
                "part_of_speech": "Noun",
                "definitions": ["A greeting."],
            }
        ]
        fake_japanese.return_value = [
            {
                "japanese": "今日は（こんにちは）",
                "glosses": ["hello", "good day"],
                "parts_of_speech": [],
            }
        ]

        define_command_callback(
            {"text": "hello"},
            ack=self.fake_ack,
            respond=self.fake_respond,
            logger=test_logger,
        )

        self.fake_ack.assert_called_once()
        kwargs = self.fake_respond.call_args.kwargs
        assert kwargs["text"] == "Definitions of hello"
        blocks = kwargs["blocks"]
        assert blocks[0]["text"]["text"] == "hello"
        body = "\n".join(block.get("text", {}).get("text", "") for block in blocks)
        assert "*English (Wiktionary)*" in body
        assert "A greeting." in body
        assert "*日本語 (Jisho)*" in body
        assert "今日は（こんにちは）" in body
        sources = blocks[-1]["elements"][0]["text"]
        assert "Wiktionary" in sources
        assert "Jisho" in sources

    @patch("listeners.commands.define_command.fetch_japanese_meanings")
    @patch("listeners.commands.define_command.fetch_english_definitions")
    def test_not_found(self, fake_english, fake_japanese):
        fake_english.side_effect = WordNotFoundError("xyzzy")
        fake_japanese.return_value = []

        define_command_callback(
            {"text": "xyzzy"},
            ack=self.fake_ack,
            respond=self.fake_respond,
            logger=test_logger,
        )

        self.fake_respond.assert_called_once()
        assert "No definition found" in self.fake_respond.call_args.args[0]

    @patch("listeners.commands.define_command.fetch_japanese_meanings")
    @patch("listeners.commands.define_command.fetch_english_definitions")
    def test_jisho_error_still_returns_english(self, fake_english, fake_japanese):
        fake_english.return_value = [
            {
                "part_of_speech": "Noun",
                "definitions": ["A greeting."],
            }
        ]
        fake_japanese.side_effect = JishoRequestError("down")

        define_command_callback(
            {"text": "hello"},
            ack=self.fake_ack,
            respond=self.fake_respond,
            logger=test_logger,
        )

        blocks = self.fake_respond.call_args.kwargs["blocks"]
        body = "\n".join(block.get("text", {}).get("text", "") for block in blocks)
        assert "A greeting." in body
        assert "Jisho に接続できませんでした。" in body

    @patch("listeners.commands.define_command.fetch_japanese_meanings")
    @patch("listeners.commands.define_command.fetch_english_definitions")
    def test_both_sources_unavailable(self, fake_english, fake_japanese):
        fake_english.side_effect = WiktionaryRequestError("down")
        fake_japanese.side_effect = JishoRequestError("down")

        define_command_callback(
            {"text": "hello"},
            ack=self.fake_ack,
            respond=self.fake_respond,
            logger=test_logger,
        )

        assert "couldn't reach Wiktionary or Jisho" in self.fake_respond.call_args.args[0]
