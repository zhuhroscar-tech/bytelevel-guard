"""bytelevel-guard: catch ByteLevel-BPE added-token corruption before it ships.

Detects tokens/strings that hit the known GPT-2/RoBERTa/Qwen/Mistral
ByteLevel-BPE decoder truncation bug where certain remapped Unicode
characters (originally standing in for control-range bytes 0x00-0x20,
0x7f, 0x80-0xa0) get corrupted back to raw control characters when added
as custom vocabulary/added_tokens and decoded by the Rust "fast" tokenizer
backend. See https://github.com/huggingface/tokenizers/issues/1996.
"""

from bytelevel_guard.bytelevel import (
    bytes_to_unicode,
    remapped_char_to_byte,
    scan_text_for_risky_chars,
    unicode_to_bytes,
)

__version__ = "0.1.4"

__all__ = [
    "bytes_to_unicode",
    "unicode_to_bytes",
    "remapped_char_to_byte",
    "scan_text_for_risky_chars",
    "__version__",
]
