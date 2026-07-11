"""Self-check for Lua result parsing. Run: python test_allowed_parse.py"""


def parse_allowed(allowed) -> bool:
    return int(allowed) == 1


assert parse_allowed(1) is True
assert parse_allowed(0) is False
assert parse_allowed("1") is True
assert parse_allowed("0") is False
assert bool("0") is True, "sanity: bool('0') is wrong for Redis string zero"

print("OK: allowed parsing self-check passed")
