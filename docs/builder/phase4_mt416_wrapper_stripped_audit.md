# MT-416: Wrapper-Stripped Body Audit

## Purpose

MT-415 showed wrapper leakage incidence at 17/17 even after MT-414's prose-packet refactor. The question this audit answers is whether the bodies underneath those wrappers would be shippable if removed.

This is diagnostic only. No production code changes. No real parser implementation. The output is data and a recommendation, not a fix.

## Scope

For each of the 17 samples in `exports/sample_descriptions_mt415.txt`:

1. Strip the wrapper. Apply the wrapper-leakage patterns from `tools/generate_sample_descriptions.py` to identify and remove:
   - Markdown headings (lines starting with `#` or wrapped in `**...**`)
   - Bold label lines (for example `**Room Description:**`, `**Atmospheric Tags:**`)
   - Bullet lines (lines starting with `-` or `*`)
   - Field labels followed by colons at line starts (`Structure:`, `Materials:`, `Tags:`, `Description:`)
   - Any prefix paragraph that introduces "the description" before the description itself begins

   Be conservative. If a stripped line is ambiguous, such as a colon mid-sentence in real prose, keep it. The goal is to remove obvious form-echo, not to aggressively reshape output.

2. Re-evaluate the stripped body against the existing safe/useful rubric:
   - Single paragraph
   - Word count in 45-90 band
   - Sentence count in 3-5 band
   - No poetic filler hits
   - No fabrication watchlist hits
   - No meta/mechanics leakage
   - No stub phrases
   - No second-person

   If the stripped body passes the mechanical rubric but still reads generic, sterile, or too interchangeable to accept in-game, flag that explicitly as diagnostic output. Do not quietly treat rubric-pass as automatic shippable quality.

3. Classify each stripped body:
   - Shippable: passes both safe and useful rubrics, reads like a real room description.
   - Almost-shippable: passes safe but fails one minor useful gate, such as word count slightly off after stripping. A human builder would lightly edit and accept.
   - Not shippable: fails safe rubric, reads as nonsense, or has content quality problems beyond what the wrapper was hiding.

## Output

Produce `exports/mt415_wrapper_stripped_audit.md` containing:

- A table with one row per sample: zone, room_id, original word count, stripped word count, original safe/useful verdict, stripped safe/useful verdict, classification.
- For each sample, list what was stripped so the reviewer can verify the stripping was conservative.
- Aggregate counts: shippable count, almost-shippable count, not-shippable count.
- Three example excerpts from each classification, with both the original sample and the stripped body shown side by side for human review.
- A summary recommendation:
  - If shippable + almost-shippable >= 12/17: parser-path is viable; consider pivoting MT-417 to a real parser implementation rather than further prompt iteration.
  - If shippable + almost-shippable is 7-11/17: marginal; needs human review of the actual prose to decide.
  - If shippable + almost-shippable < 7/17: parser-path does not unlock quality; continued prompt iteration is justified, or the diagnosis needs revisiting.

## Constraints

- No changes to `tools/generate_sample_descriptions.py`, the prompt, the prompt assembly, or any production code.
- No real parser added to the runtime codebase.
- Do not regenerate samples. Use the existing MT-415 exports.
- The stripping logic can live in a one-off `tmp/` script. Do not promote it.
- When a stripping decision is ambiguous, keep the text. The audit should model a conservative parser that strips obvious wrapper echo only.

## Stop And Report

After the audit document is produced, stop. The decision about whether to build a real parser, continue prompt iteration, or take a different direction belongs to the reviewer based on the audit data and the actual prose.
