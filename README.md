# HTTP Header Token Parser

Parses HTTP header values into an ordered list of RFC 7230 token and quoted-string elements, handling backslash-escaping and obs-fold.

```python
from http_header_token_parser import parse_header_value, HeaderValue, Token

hv: HeaderValue = parse_header_value('gzip "identity;q=0" br')
for el in hv:
    print(el.value, el.is_quoted)
# gzip False
# identity;q=0 True
# br False
```

## Why this exists

`str.split()` and `str.split(",")` are the usual ways people read header values, and both break on quoted-strings that contain spaces or separators. This library parses one header value at a time into `Token` elements, each carrying its unescaped string value and whether it was quoted. It does **not** split on commas — that is the caller's job, because comma-splitting semantics differ between headers (e.g. `Accept` vs. `Set-Cookie`). Parse each comma-separated part with this library if you need token/quoted-string handling within it.

The trade-off: a deliberately small surface. No Q-value sorting, no parameter extraction, no media-type parsing. Just tokens and quoted-strings, correctly unescaped.

## Awkward edge

A token that contains a comma (e.g. `gzip,deflate` as a single value) raises `ValueError`. The parser treats a header value as a whitespace-delimited sequence of tokens and quoted-strings only; commas are not separators here. If your header is comma-delimited, split on commas first, then call `parse_header_value` on each piece.
