"""Flag two members quoting the same words of the advisory but reading different values.

A verified quotation proves the words are there, not that the value is right.
Where two members' verified quotations are the same words and their values differ,
one sentence was read two ways. This is shown beside the council, never used by it.
Words are folded as the quotation check folds them (`council.evidence.normalise`);
two quotations are the same when one equals the other or sits inside it without
cutting into a word.
"""

import re
from itertools import combinations
from typing import Sequence

from council.answer import MemberAnswer, MemberReply
from council.evidence import WORD_CHARACTER, is_quotation_from, normalise

# No word character may sit either side of the shorter quotation: `path` is not in `paths`.
NO_WORD_BEFORE = r"(?<!\w)"
NO_WORD_AFTER = r"(?!\w)"


def read_differently(replies: Sequence[MemberReply], advisory_text: str) -> bool:
    """Say whether two members quoted the same verified words and read different values."""
    verified = [one for one in replies if is_verified_answer(one, advisory_text)]
    return any(
        one.value != other.value and same_words(one.evidence, other.evidence)
        for one, other in combinations(verified, 2)
    )


def is_verified_answer(reply: MemberReply, advisory_text: str) -> bool:
    """Say whether a reply is an answer whose quotation the advisory contains."""
    if not isinstance(reply, MemberAnswer):
        return False
    return is_quotation_from(reply.evidence, advisory_text)


def same_words(one: str, other: str) -> bool:
    """Say whether two quotations are the same words: one equal to, or inside, the other."""
    shorter, longer = sorted((normalise(one), normalise(other)), key=len)
    if not shorter:
        raise ValueError("A quotation with no text cannot be the same words as another")
    return re.search(whole_words(shorter), longer) is not None


def whole_words(quotation: str) -> str:
    """Give a pattern finding a quotation as text, never cutting into a word at either end."""
    before = NO_WORD_BEFORE if WORD_CHARACTER.match(quotation[0]) else ""
    after = NO_WORD_AFTER if WORD_CHARACTER.match(quotation[-1]) else ""
    return f"{before}{re.escape(quotation)}{after}"
