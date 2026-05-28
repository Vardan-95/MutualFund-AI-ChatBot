from __future__ import annotations


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    try:
        import tiktoken

        enc = tiktoken.get_encoding(encoding_name)
        return len(enc.encode(text))
    except Exception:
        return max(1, len(text.split()) * 4 // 3)
