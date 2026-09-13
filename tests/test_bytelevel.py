"""Independent oracle: recompute GPT-2 bytes_to_unicode from scratch and
cross-check against the shipped implementation, plus verify the exact
real-world corruption cases reported in tokenizers#1996.
"""
from bytelevel_guard.bytelevel import (
    bytes_to_unicode,
    remapped_char_to_byte,
    scan_text_for_risky_chars,
    unicode_to_bytes,
)


def _reference_bytes_to_unicode() -> dict[int, str]:
    """A from-scratch reimplementation (not imported from the package under
    test) of OpenAI's original gpt-2/src/encoder.py bytes_to_unicode(), used
    as an independent oracle."""
    bs = []
    for b in range(ord("!"), ord("~") + 1):
        bs.append(b)
    for b in range(0xA1, 0xAC + 1):
        bs.append(b)
    for b in range(0xAE, 0xFF + 1):
        bs.append(b)
    cs = list(bs)
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {b: chr(c) for b, c in zip(bs, cs)}


def test_table_matches_independent_oracle():
    oracle = _reference_bytes_to_unicode()
    impl = bytes_to_unicode()
    assert oracle == impl


def test_table_covers_all_256_bytes_bijectively():
    table = bytes_to_unicode()
    assert len(table) == 256
    assert len(set(table.values())) == 256  # bijective, no collisions


def test_printable_ascii_and_latin1_glyphs_are_identity_mapped():
    table = bytes_to_unicode()
    # '!' (0x21) through '~' (0x7e) must map to themselves unchanged.
    for b in range(ord("!"), ord("~") + 1):
        assert table[b] == chr(b)


def test_control_range_bytes_are_remapped_above_u0100():
    table = bytes_to_unicode()
    for b in list(range(0x00, 0x21)) + [0x7F] + list(range(0x80, 0xA1)) + list(
        range(0xAD, 0xAE)
    ):
        assert ord(table[b]) >= 0x100, f"byte {hex(b)} should be remapped but got {table[b]!r}"


def test_unicode_to_bytes_is_exact_inverse():
    b2u = bytes_to_unicode()
    u2b = unicode_to_bytes()
    for b, ch in b2u.items():
        assert u2b[ch] == b


# --- Exact real-world regression cases from
# https://github.com/huggingface/tokenizers/issues/1996 ---

def test_regression_c_caron_corrupts_to_carriage_return():
    # 'č' U+010D is the reported remap of byte 0x0D ('\r').
    hits = scan_text_for_risky_chars("č")
    assert len(hits) == 1
    idx, ch, byte = hits[0]
    assert ch == "č"
    assert byte == 0x0D
    assert chr(byte) == "\r"


def test_regression_c_acute_corrupts_to_bell():
    # 'ć' U+0107 is the reported remap of byte 0x07 (BEL).
    hits = scan_text_for_risky_chars("ć")
    assert len(hits) == 1
    assert hits[0][2] == 0x07


def test_regression_d_stroke_corrupts_to_dc1():
    # 'đ' U+0111 is the reported remap of byte 0x11 (DC1).
    hits = scan_text_for_risky_chars("đ")
    assert len(hits) == 1
    assert hits[0][2] == 0x11


def test_regression_real_world_words_from_issue():
    # The exact three example words from tokenizers#1996.
    assert len(scan_text_for_risky_chars("Začnimo")) == 1
    assert len(scan_text_for_risky_chars("kuća")) == 1
    assert len(scan_text_for_risky_chars("međa")) == 1


def test_safe_ascii_word_has_no_hits():
    assert scan_text_for_risky_chars("hello_world") == []


def test_safe_ordinary_unicode_word_has_no_hits():
    # Ordinary CJK / accented characters outside the U+0100-U+0142-ish
    # remap range used by the byte table must not false-positive.
    assert scan_text_for_risky_chars("東京") == []
    assert scan_text_for_risky_chars("café") == []  # 'é' not in remap range


def test_remapped_char_to_byte_excludes_identity_mapped_chars():
    table = remapped_char_to_byte()
    assert "a" not in table
    assert "!" not in table
    assert "č" in table
