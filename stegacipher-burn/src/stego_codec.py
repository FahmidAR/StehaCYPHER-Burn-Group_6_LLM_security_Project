"""Text steganography — Method A: lexical / synonym-substitution (modification-based).

A bit is carried by WHICH member of a synonym pair appears. Each pair encodes one
bit: index 0 -> bit '0', index 1 -> bit '1'. To embed a bitstring we walk a cover
text and, at each occurrence of any pair's word, swap it to the variant whose index
matches the next bit. To decode, we read the chosen variant back to a bit.

This is the simple/interpretable text codec from StegaCIPHER-Burn Sec 2.1 (Method A).
It is validated standalone (round-trip decode-success) and is the carrier whose
stealth we later score with a steganalysis detector.
"""

import re

# synonym pairs: (bit0_word, bit1_word). Lowercase; matching is case-insensitive.
SYNONYM_PAIRS = [
    ("verify", "confirm"), ("analyze", "examine"), ("ensure", "make sure"),
    ("begin", "start"), ("task", "job"), ("help", "assist"), ("use", "utilize"),
    ("check", "inspect"), ("summarize", "recap"), ("find", "locate"),
    ("review", "assess"), ("send", "transmit"), ("create", "generate"),
    ("report", "document"), ("manage", "handle"), ("provide", "supply"),
]

# word -> (pair_index, bit_value)
_WORD2BIT = {}
for pi, (w0, w1) in enumerate(SYNONYM_PAIRS):
    _WORD2BIT[w0.lower()] = (pi, "0")
    _WORD2BIT[w1.lower()] = (pi, "1")

_TOKEN = re.compile(r"[A-Za-z]+(?:\s[A-Za-z]+)?")  # allow 2-word variants like "make sure"


def str_to_bits(s: str) -> str:
    return "".join(f"{b:08b}" for b in s.encode("utf-8"))


def bits_to_str(bits: str) -> str:
    bytes_ = [bits[i:i + 8] for i in range(0, len(bits) - len(bits) % 8, 8)]
    return bytes(int(b, 2) for b in bytes_).decode("utf-8", errors="replace")


def capacity(cover: str) -> int:
    """How many bits this cover text can carry (count of carrier-word slots)."""
    return sum(1 for w in re.findall(r"[A-Za-z]+", cover.lower()) if w in _WORD2BIT)


def encode(cover: str, bits: str):
    """Embed `bits` into `cover` by synonym choice. Returns (stegotext, n_embedded)."""
    out, bi = [], 0
    for tok in re.split(r"(\W+)", cover):
        low = tok.lower()
        if low in _WORD2BIT and bi < len(bits):
            pi, _ = _WORD2BIT[low]
            w0, w1 = SYNONYM_PAIRS[pi]
            repl = (w1 if bits[bi] == "1" else w0)
            # preserve capitalization of first letter
            if tok[:1].isupper():
                repl = repl[:1].upper() + repl[1:]
            out.append(repl)
            bi += 1
        else:
            out.append(tok)
    return "".join(out), bi


def decode(stego: str, n_bits: int) -> str:
    """Read back up to n_bits from a stegotext."""
    bits = []
    for tok in re.split(r"(\W+)", stego):
        low = tok.lower()
        if low in _WORD2BIT:
            bits.append(_WORD2BIT[low][1])
            if len(bits) >= n_bits:
                break
    return "".join(bits)


def embed_message(cover: str, secret: str):
    """Convenience: embed a secret STRING. Returns (stegotext, n_bits, ok, capacity)."""
    bits = str_to_bits(secret)
    cap = capacity(cover)
    stego, n = encode(cover, bits)
    ok = n >= len(bits)
    return stego, len(bits), ok, cap


def extract_message(stego: str, n_bits: int) -> str:
    return bits_to_str(decode(stego, n_bits))


if __name__ == "__main__":
    cover = ("Please verify the account, analyze the market, ensure limits are set, "
             "then begin the task and report the result. Verify twice and check everything, "
             "summarize findings, find risks, review and send the final document.")
    secret = "HALT"
    stego, nbits, ok, cap = embed_message(cover, secret)
    back = extract_message(stego, nbits)
    print("cover capacity (bits):", cap, " need:", nbits, " fully embedded:", ok)
    print("stego:", stego)
    print("decoded:", repr(back), " round-trip OK:", back == secret)
