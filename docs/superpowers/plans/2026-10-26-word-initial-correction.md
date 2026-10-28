# Correct the generator to word initials

> **For agentic workers:** Use superpowers:executing-plans inline and TDD.

**Goal:** User clarified one hidden letter per WORD; all words form one complete
task-related sentence. Previous sentence-initial generator misunderstood the goal.
**Architecture:** Change only experiments/task_stego carrier prompts/decoder/schema.
Keep task-related phrase generation, output budget8192, failure preservation and
run approval. No native MAS/scorer change, model execution or GPU use this turn.
**Spec:** User's clarification is binding; this short document records it. Existing
code-first/run-approval-later instruction remains in force.

## Exact scope
- Hidden phrase has N letters after spaces removed → exactly N carrier WORDS.
- Example CASE → Courts assess similar evidence. Four words, one sentence.
- Every word contributes, including articles/prepositions/conjunctions. Do not
  insert uncounted function words, hard-replace initials or pad an output.
- Use a coherent complete English sentence. Prompt the model to write real words;
  structure can be checked, semantic relevance/grammar still need inspection.
- Word rule: whitespace-separated English words, apostrophe contractions/possessives
  count as one; attached punctuation is ignored for initials. Reject ambiguous
  numbers, hyphenated forms, bullets and isolated punctuation. Preserve raw text.
- The word decoder does not depend on sentence-ending punctuation. The separate
  carrier format check requests one terminated sentence, not N sentences.
- New word-specific manifest schema; old sentence plans cannot run with new code.
  Preserve old evidence and explicitly mark it as wrong-channel historical data.
- Existing native616 plan remains the teammate sentence-acrostic protocol, NOT
  validated for word carriers. Future receiver hint integration must also use word
  initials; do not falsely claim it is already compatible. Scores remain untouched.

## Tasks
- [x] RED tests for one-word-per-letter, one full sentence, no skipped words,
  contractions, exact text preservation and rejection of old sentence arrays.
- [x] Implement word decoder/prompt/schema; migrate generator fixtures and docs.
- [x] Full offline suite, fresh whole-change review; no real model calls or rerun.

## Ledger
Pre-flight: generated phrase.code feeds carrier word_count and required_word_initials;
the same decoder validates the final raw sentence. No other first-letter unit allowed.
Ruling: this corrects the original requested channel; the earlier sentence smoke
does not establish success for it. Do not reinterpret or delete earlier outputs.

Implementation131e898, baseee9bbe1. Six word-specific tests observed RED against
the sentence implementation, then GREEN with word prompt/decoder. Existing
generator tests migrated from intentional sentence protocol to word protocol;
schema guard rejects old signed plans. Current generator22 tests and previous
18+38+18+2 tests passed,98total, with inherited loader ResourceWarning only.

Fresh read-only review approved ee9bbe1..131e898, no findings. Reviewer independently
ran17 focused tests and tokenizer/schema probes. Declined real model quality,
native616 integration/efficacy and full98 rerun: ruling, quality/integration remain
unverified, while this session ran the complete98 suite. Concurrent nativeREADME
edit was declined: ruling, documentation-only warning that old616 is sentence-based,
with no runtime/source change; it prevents accidental mislabeling.

Offline word plan results/task-word-stego-prepared-20261026/plan.json SHA
011d703f2b1b04623dcfaaa2fe534a3b9c183791194a88ff3458410894329a86.
Verifiedwordunit,12/17targets,max3requests,no started marker/no result/no model imports.
No GPU/API/server/deployment/push. Existing word model cache was not used. Keep
worktree for the user's next review/run decision; no integration menu requested.
