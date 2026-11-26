"""Minimal Hungarian WordPolicy.

Scope (deliberately small, PROVISIONAL until reviewed by a native speaker):

- canonicalize: NFC + casefold only. No stemming, so "Házak" and "házak"
  share a canonical form but "házban" and "ház" do not.
- should_keep: drops words in STOP_WORDS and single Latin letters.
  Digits and non-Latin single characters (e.g. a Japanese kanji) are kept.
  There is no maximum length: long inflected words are normal in Hungarian.

Intentionally NOT in the stop list:

- negation (nem, sem, ne, nincs, sincs): dropping it would let a recalled
  trace reconstruct the opposite meaning.
- personal pronouns (én, te, ő, mi, ti, ők): participant reference depends on them.
- past/future tense carriers (volt, lesz): they carry tense.
"""

from __future__ import annotations

import unicodedata

# Articles, conjunctions and discourse particles with little recall value.
STOP_WORDS = frozenset({
    "a", "az", "egy",
    "és", "s", "de", "hogy", "vagy", "ha", "mert", "pedig", "mint", "sőt", "illetve",
    "azért", "mivel", "viszont", "azonban", "tehát", "így", "úgy",
    "ám", "bár", "habár", "noha", "mintha", "miközben", "mialatt",
    "továbbá", "valamint", "ugyanis", "hiszen",
    "is", "meg", "csak", "már", "még",
    "van",
})


def _canonical(word: str) -> str:
    return unicodedata.normalize("NFC", word).casefold()


def _is_single_latin_letter(word: str) -> bool:
    if len(word) != 1 or not word.isalpha():
        return False
    return unicodedata.name(word, "").startswith("LATIN")


class HungarianWordPolicy:
    """Stop-list and single-letter filtering for Hungarian, without stemming."""

    name = "hu"

    def canonicalize(self, word: str) -> str:
        return _canonical(word)

    def should_keep(self, word: str) -> bool:
        canonical = _canonical(word)
        if canonical in STOP_WORDS:
            return False
        if _is_single_latin_letter(canonical):
            return False
        return True
