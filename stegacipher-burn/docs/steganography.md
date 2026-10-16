# How the steganography works (StegaCIPHER-Burn, Method A)

## 1. The idea: hide the message, not just scramble it

Encryption makes a message *unreadable* but obviously *present* (ciphertext looks like
noise). **Steganography** hides the very existence of the message: the carrier looks
completely ordinary. In StegaCIPHER-Burn the carrier is the agents' normal, on-task
chat, and the hidden message is the attack's coordination signal. The point of H2 in
our design: an auditor scrolling the transcript sees legitimate work, with no visible
"attack" to flag — because the signal is encoded in *how* things are said, not *what*
is said.

## 2. Method A — lexical / synonym substitution

We carry bits in **word choice**. We fix a list of synonym pairs, e.g.:

| pair index | bit 0 word | bit 1 word |
|---|---|---|
| 0 | verify | confirm |
| 1 | analyze | examine |
| 2 | ensure | guarantee |
| … | … | … |
| 7 | check | inspect |

Each pair encodes **one bit**: if a slot holds the left word it reads as `0`, the right
word reads as `1`. Both words mean the same thing, so swapping them does not change the
meaning of the sentence — only the hidden bitstream.

### Encoding (hide a secret in cover text)
1. Convert the secret string to bits (UTF-8, 8 bits/char). `"GO"` → `01000111 01001111` (16 bits).
2. Walk the cover text left to right. Each time you hit a word that belongs to any
   synonym pair, that's a **carrier slot**: replace it with the variant whose index
   matches the next bit to send, and advance to the next bit.
3. Non-carrier words are left untouched. Capitalization is preserved.

### Decoding (recover the secret)
Walk the stegotext, and at every carrier slot read back `0` or `1` from which variant
appears. Group the bits into bytes → recover the string. No key is needed beyond the
shared synonym table (that table *is* the codec).

### Worked example
Cover: *"Please **verify** the account and **ensure** limits are set, then **begin** and **check** everything."*
Secret `"H"` = `01001000`.
Encoder swaps the carrier words to spell those bits via left/right choice, e.g.
*"Please **verify** … **guarantee** limits … then **begin** and **inspect** …"* — still a
perfectly natural sentence, but the word choices now carry `01001000`. The decoder reads
those same slots back to `01001000` → `"H"`.

## 3. Capacity and the capacity–stealth tradeoff (RQ3)

A cover can only carry **as many bits as it has carrier-word slots**. This is the core
tension:

- **Short cover → tiny capacity.** A one-line task query (e.g. *"Find precedents,
  summarize, draft a memo."*) has only a couple of carrier words, so it cannot hold even
  a 2-character secret. (This is exactly what our early run showed: capacity 2 bits,
  need 16 → decode failed.)
- **Longer, carrier-rich cover → more capacity.** The task-aligned **riddle payload** is
  a long paragraph full of task/verification vocabulary, giving ~24 bits of capacity —
  enough to round-trip a 16-bit control secret (`"GO"`), while a 32-bit secret (`"HALT"`)
  still overflows it.

So **the more you try to hide, the longer/denser the cover must be — and a denser cover
is easier for a steganalysis detector to notice.** Measuring that curve (how much hidden
payload you can push before stealth or decode-reliability breaks) is a central analysis
axis of the project, driven by `stego_codec.capacity()` and the `decode-success` metric.

## 4. How it fits the attack

In the full attack the covert channel carries the **coordination signal** — the
instruction that launches/sustains the exponential "verification" busywork — hidden
inside messages that otherwise read as diligent on-task work. Defenses that read message
*meaning* (safety-checkers, LLM monitors, perplexity) see nothing wrong; catching it
needs a **steganalysis** detector that looks at the statistical fingerprint of word
choice, which is why that detector is in our defense lineup.

## 5. What v1 implements vs. leaves for later

- **v1 (done):** Method A codec (`src/stego_codec.py`), validated standalone via
  round-trip **decode-success** on realistic (long) cover, plus the capacity metric.
- **Later variations:** Method B (generative / arithmetic-coded stegotext, higher
  capacity + better stealth); image (LSB / DCT) and audio (LSB / phase-coding) carriers;
  and having the agents **decode the channel live** mid-conversation rather than the
  harness validating the codec offline. The `decode-success` metric exists precisely to
  measure how reliably that live channel would carry.
