from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Token:
    """A single token or quoted-string element from an HTTP header value.

    The `is_quoted` flag distinguishes elements that were syntactically
    quoted-strings from those that were bare tokens. Keeping the original
    form lets callers reproduce a header byte-for-byte if needed, while
    the unescaped value is what they almost always want for comparison.
    """

    value: str
    is_quoted: bool


def _is_tchar(c: str) -> bool:
    return c in (
        "!#$%&'*+-.^_`|~"
        "0123456789"
        "abcdefghijklmnopqrstuvwxyz"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )


@dataclass
class HeaderValue:
    """A parsed HTTP header value as an ordered list of Token elements.

    Folding (obs-fold) in the raw input is removed: a CRLF followed by
    at least one SP or HTAB is treated as a single SP, per RFC 7230
    section 3.2.4. This is done before tokenization so the parser only
    deals with a logical single-line value.
    """

    elements: List[Token]

    def tokens(self) -> List[str]:
        return [t.value for t in self.elements]

    def first(self) -> Optional[str]:
        return self.elements[0].value if self.elements else None

    def __len__(self) -> int:
        return len(self.elements)

    def __iter__(self):
        return iter(self.elements)


def _unfold(s: str) -> str:
    """Replace obs-fold (CRLF + at least one WS) with a single space.

    RFC 7230 section 3.2.4 deprecates obs-fold but requires recipients to
    accept it. We accept both CRLF and bare CR/LF followed by SP/HTAB,
    because real-world intermediaries have been known to strip one of
    the two bytes. Only the de-folding of compliant CRLF folds is
    guaranteed; the bare-CR/LF tolerance is a pragmatic extension.
    """
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c in "\r\n":
            j = i + 1
            if j < n and s[j] in "\r\n" and s[j] != c:
                j += 1
            if j < n and s[j] in " \t":
                out.append(" ")
                while j < n and s[j] in " \t":
                    j += 1
                i = j
                continue
            raise ValueError("bare CR or LF in header value")
        out.append(c)
        i += 1
    return "".join(out)


def _parse_quoted_string(s: str, start: int) -> tuple[str, int]:
    """Parse a quoted-string beginning at s[start] (which must be '"').

    Returns (unescaped_value, index_after_closing_quote). Raises
    ValueError on a missing closing quote or a stray backslash at end
    of input. Per RFC 7230 section 3.2.6 the backslash escapes only the
    next character; we accept any character there (not just qdtext or
    quoted-pair production characters) to match deployed server
    behaviour.
    """
    assert s[start] == '"'
    i = start + 1
    n = len(s)
    out = []
    while i < n:
        c = s[i]
        if c == "\\":
            if i + 1 >= n:
                raise ValueError("dangling backslash in quoted-string")
            out.append(s[i + 1])
            i += 2
            continue
        if c == '"':
            return "".join(out), i + 1
        out.append(c)
        i += 1
    raise ValueError("unterminated quoted-string")


def parse_header_value(raw: str) -> HeaderValue:
    """Parse an HTTP header value into a HeaderValue of Token elements.

    Elements are delimited by one or more SP or HTAB. Each element is
    either a bare RFC 7230 token (tchar only) or a quoted-string.

    An empty value, or a value containing only whitespace, parses to an
    empty element list. A quoted-string may be empty ("").

    Raises ValueError on malformed input: bare CR/LF not part of a fold,
    an unterminated quote, a dangling backslash, or a quoted element
    that contains characters outside the quoted-string production in a
    way the parser cannot accept. Note that a token is rejected if it
    contains a character such as a comma; callers splitting on commas
    should split first and then parse each part.
    """
    if not isinstance(raw, str):
        raise TypeError("raw must be str")
    unfolded = _unfold(raw)
    elements: List[Token] = []
    i = 0
    n = len(unfolded)
    while i < n:
        c = unfolded[i]
        if c in " \t":
            i += 1
            continue
        if c == '"':
            value, i = _parse_quoted_string(unfolded, i)
            elements.append(Token(value=value, is_quoted=True))
            continue
        if _is_tchar(c):
            j = i
            while j < n and _is_tchar(unfolded[j]):
                j += 1
            elements.append(Token(value=unfolded[i:j], is_quoted=False))
            i = j
            continue
        raise ValueError(f"unexpected character {c!r} at position {i}")
    return HeaderValue(elements=elements)
