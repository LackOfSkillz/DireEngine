# MT-415: Live Sampler Rerun After MT-414 Prompt-Shape Refactor

## Ready-To-Send Dispatch

```text
Proceed with MT-415 only.

MT-415 — Live sampler rerun after MT-414 prompt-shape refactor.

Acceptance source:
docs/builder/phase4_mt414_prompt_shape_handoff.md for the MT-414 baseline/intent, but this task is execution/reporting only.

Goal:
Measure whether the MT-414 prose-style prompt packet reduced wrapper/form leakage in real generated room descriptions.

This is a live evaluation task only.

Do not change prompt wording.
Do not change sampler scoring.
Do not change room YAML.
Do not import generated descriptions.
Do not batch apply descriptions.
Do not tune model output.
Do not change LM Studio settings.
Do not change the default LLM endpoint.
Do not add post-processing that strips bad output.

Use the localhost override:

$env:LLM_BASE_URL='http://127.0.0.1:1234'

Current failure baseline from the latest MT-413 rerun:
- Generated samples: 17
- Safe samples: 0/17
- Useful samples: 0/17
- Useful acceptance rate: 0.0%
- Average words: 64.82
- under_45_words: 1
- 45_to_90_words: 16
- over_90_words: 0
- under_3_sentences: 0
- 3_to_5_sentences: 17
- over_5_sentences: 0
- poetic filler total: 6
- fabrication watchlist total: 2
- stub phrase total: 0
- wrapper leakage total: 61
- wrapper-affected samples: 17/17

Run exactly:

$env:LLM_ENABLED='true'; $env:LLM_BASE_URL='http://127.0.0.1:1234'; c:/Users/gary/dragonsire/.venv/Scripts/python.exe tools/generate_sample_descriptions.py --zones=demo1 --limit=6 --output exports/sample_descriptions_mt415_demo1.txt

$env:LLM_ENABLED='true'; $env:LLM_BASE_URL='http://127.0.0.1:1234'; c:/Users/gary/dragonsire/.venv/Scripts/python.exe tools/generate_sample_descriptions.py --zones=crossingV2 --limit=6 --output exports/sample_descriptions_mt415_crossingV2.txt

$env:LLM_ENABLED='true'; $env:LLM_BASE_URL='http://127.0.0.1:1234'; c:/Users/gary/dragonsire/.venv/Scripts/python.exe tools/generate_sample_descriptions.py --zones=new_landing --limit=6 --output exports/sample_descriptions_mt415_new_landing.txt

Then combine:

$mt415 = foreach ($file in @('exports/sample_descriptions_mt415_demo1.txt','exports/sample_descriptions_mt415_crossingV2.txt','exports/sample_descriptions_mt415_new_landing.txt')) { Get-Content $file }
[System.IO.File]::WriteAllLines((Join-Path (Get-Location) 'exports/sample_descriptions_mt415.txt'), $mt415)

Required report:
- Generated samples: X
- Safe samples: X/Y
- Useful samples: X/Y
- Useful acceptance rate: N.N%
- Average word count
- under_45_words
- 45_to_90_words
- over_90_words
- under_3_sentences
- 3_to_5_sentences
- over_5_sentences
- poetic filler total
- fabrication watchlist total
- stub phrase total
- wrapper leakage total
- wrapper-affected sample count

Compare directly against the latest MT-413 baseline:
- Safe samples: 0/17
- Useful samples: 0/17
- Average words: 64.82
- 45_to_90_words: 16/17
- 3_to_5_sentences: 17/17
- poetic filler total: 6
- fabrication watchlist total: 2
- stub phrase total: 0
- wrapper leakage total: 61
- wrapper-affected samples: 17/17

Also include:
- best 3 generated descriptions
- worst 3 generated descriptions
- brief diagnosis:
  - Did wrapper leakage improve?
  - Are outputs still correctly 3–5 sentences?
  - Are outputs still 45–90 words?
  - Are outputs grounded?
  - Are remaining failures caused by wrapper leakage, unsupported props/details, filler, length, sentence count, or stubs?

Acceptance target:
- Safe samples >= 90%
- Useful samples >= 70%
- Average words between 55 and 80
- Poetic filler total = 0
- Fabrication watchlist total = 0
- Stub phrase total = 0
- Wrapper leakage total = 0 or near-zero

If the batch fails:
- Do not patch anything.
- Report the failure mode clearly.
- Recommend the smallest next MT-416 change.

Return with:

MT-415 complete.

Files created:
- ...

Metrics:
- ...

Comparison to MT-413 baseline:
- ...

Best samples:
- ...

Worst samples:
- ...

Diagnosis:
- ...

Production code changed:
- no

Compatibility risks:
- ...
```

## Guardrail

```text
Stop after reporting MT-415. Do not proceed to MT-416. Do not patch prompt/scoring based on the results until the report is reviewed.
```
