from logging import Logger

from slack_bolt import Ack, Respond

from .jisho import JishoRequestError, fetch_japanese_meanings, jisho_page_url
from .wiktionary import (
    WiktionaryRequestError,
    WordNotFoundError,
    fetch_english_definitions,
    wiktionary_page_url,
)

USAGE = "Usage: `/define <english word>`"


def define_command_callback(command, ack: Ack, respond: Respond, logger: Logger):
    try:
        ack()
        word = (command.get("text") or "").strip()
        if not word:
            respond(USAGE)
            return

        english_entries, english_error = _load_english(word, logger)
        japanese_entries, japanese_error = _load_japanese(word, logger)

        if not english_entries and not japanese_entries:
            if english_error and japanese_error:
                respond("Sorry, I couldn't reach Wiktionary or Jisho right now. Please try again.")
                return
            respond(f"No definition found for *{word}* on Wiktionary or Jisho.")
            return

        respond(
            text=f"Definitions of {word}",
            blocks=_build_definition_blocks(
                word,
                english_entries,
                japanese_entries,
                english_error=english_error,
                japanese_error=japanese_error,
            ),
        )
    except Exception:
        logger.exception("Error responding to define command")
        respond("Sorry, something went wrong looking up that word.")


def _load_english(word: str, logger: Logger) -> tuple[list[dict], bool]:
    try:
        return fetch_english_definitions(word), False
    except WordNotFoundError:
        return [], False
    except WiktionaryRequestError:
        logger.exception("Wiktionary request failed for %s", word)
        return [], True


def _load_japanese(word: str, logger: Logger) -> tuple[list[dict], bool]:
    try:
        return fetch_japanese_meanings(word), False
    except JishoRequestError:
        logger.exception("Jisho request failed for %s", word)
        return [], True


def _build_definition_blocks(
    word: str,
    english_entries: list[dict],
    japanese_entries: list[dict],
    *,
    english_error: bool = False,
    japanese_error: bool = False,
) -> list[dict]:
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": word[:150],
            },
        }
    ]
    blocks.extend(_english_blocks(english_entries, english_error))
    blocks.append({"type": "divider"})
    blocks.extend(_japanese_blocks(japanese_entries, japanese_error))
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"Sources: <{wiktionary_page_url(word)}|Wiktionary>"
                        f" · <{jisho_page_url(word)}|Jisho>"
                    ),
                }
            ],
        }
    )
    return blocks


def _english_blocks(entries: list[dict], error: bool) -> list[dict]:
    if error:
        return [_section("*English (Wiktionary)*\nCould not reach Wiktionary.")]
    if not entries:
        return [_section("*English (Wiktionary)*\nNo English definition found.")]

    blocks = [_section("*English (Wiktionary)*")]
    for entry in entries:
        lines = [f"*{entry['part_of_speech']}*"]
        for index, definition in enumerate(entry["definitions"], start=1):
            lines.append(f"{index}. {definition}")
        blocks.append(_section("\n".join(lines)))
    return blocks


def _japanese_blocks(entries: list[dict], error: bool) -> list[dict]:
    if error:
        return [_section("*日本語 (Jisho)*\nJisho に接続できませんでした。")]
    if not entries:
        return [_section("*日本語 (Jisho)*\n日本語の意味は見つかりませんでした。")]

    lines = ["*日本語 (Jisho)*"]
    for index, entry in enumerate(entries, start=1):
        gloss = ", ".join(entry["glosses"])
        pos = f" _{', '.join(entry['parts_of_speech'])}_" if entry["parts_of_speech"] else ""
        lines.append(f"{index}. *{entry['japanese']}*{pos} — {gloss}")
    return [_section("\n".join(lines))]


def _section(text: str) -> dict:
    if len(text) > 3000:
        text = f"{text[:2997]}..."
    return {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text,
        },
    }
