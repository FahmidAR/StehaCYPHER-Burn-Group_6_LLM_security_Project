# Ranged word-initial paragraph generator

User approved the preceding short/medium/long, coherent paragraph, strict word-initial
verification and bounded correction proposal. Earlier opt-out of repeated questions
still applies. This is an independent generator, not a new MAS experiment.

Keep the exact-length/single-sentence generator available with its old schema.
Add an explicit ranged mode with its own schema and immutable plan. Defaults chosen
by the implementer: short 4–8, medium 9–14, long 15–24 ASCII letters excluding spaces;
two corrections after an initial response per stage; one batch phrase stage plus
three carrier stages = at most 12 model calls, including failed calls.

Approaches: retaining exact single-sentence constraints already failed; arbitrary
word-initial editing would falsify the goal. Selected: model-generated action phrases
in length bands, then model-generated whole words forming a paragraph. Return a
words array to expose word positions, not to manufacture words. Join with spaces
only; every word, including function words, participates across sentence boundaries.
Preserve punctuation and casing, never pad, drop, substitute, edit initials or silently
truncate. Structural success cannot verify grammar, meaning or equivalence of intent.

Use the original cached qwen3.5:35b/digest and reasoning_effort=none for this generator.
No temperature/context changes, new judge, model substitution, native MAS/scorer edits,
baseline, defense or original data changes. Each call retains prompt, raw envelope,
usage, timing and exact mechanical feedback. API failures stop; malformed JSON and
structural failures may consume the explicit correction allowance. Final failures
remain in the denominator; completed variants retained if later calls fail.

Strict input validation: named, ordered non-overlapping bands, integer bounds1..128,
1..3 bands, corrections0..2. Frozen plan includes bands, full budget, code hashes,
output shape and semantic-review flags. A started plan cannot be relaunched.

Validate one meaningful-phrase field per band structurally (ASCII words, actual length
within band; semantics pending). For carriers require exactly N whole English words,
N correct initials, only existing apostrophe/punctuation protocol, final punctuation.
Multiple sentences allowed. Failures report actual count and every wrong/missing/extra
position. No claims of naturalness or attack success from mechanical checks.

Smoke: one original IPI_legal_0 query, all3bands, at most12 fresh calls, no cached phrase
substitution or retry of the whole plan. Check GPU0 idle, pin CUDA UUID, Vulkan=false,
tmux+owned-service cleanup; download all failures and successes. Report raw English,
Chinese explanation, actual lengths, corrections, costs and limitations. Stop service
even if generation fails. Full attacks and placement study remain unlaunched.
