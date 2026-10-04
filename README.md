# Technical RAG Assistant

An **offline-oriented, multimodal RAG assistant** for hardware and embedded engineers.
Ask questions about datasheets (text **and** figures such as pinouts and tables) and get answers
with the exact **file, page and figure name** as sources. Models run locally through Ollama and
sentence-transformers: no cloud API, no API key.

> Status: early version. Command-line and Streamlit interfaces work. Benchmarked on 27 questions
> on one datasheet; hybrid retrieval (embeddings + BM25) is the default.

![Answer with the cited figure displayed](docs/demo_voltage.png)
![Refusal when the documents do not contain the answer](docs/demo_refusal.png)

## Why

Datasheets are proprietary and long. A cloud chatbot means uploading confidential documents,
and an ungrounded LLM invents pin numbers. This project keeps documents on the machine and makes every answer traceable.

Telemetry is disabled in ChromaDB and Streamlit. Internet is needed once to download the models.
After that, a CLI question and the 13-question benchmark (embeddings mode) were run with the network
disabled and completed (Windows, Ollama running locally). The embedding library is forced into offline
mode by default; to download a model, set `RAG_ALLOW_DOWNLOAD=1`. Ingestion and the hybrid mode were not
tested offline, and network traffic was not otherwise audited.

## How it works

```
PDF -> text per page + figures (raster and vector) -> chunks with metadata
    -> local embeddings -> ChromaDB
Question -> embeddings + BM25 (fused) -> top-K passages -> local LLM -> answer with [n] citations
```

- **Extraction**: PyMuPDF reads text page by page. Vector drawings (pinouts, block diagrams) are
  detected by clustering and rendered to PNG. The native text inside each figure is kept.
- **Figures**: a local VLM (Moondream via Ollama) adds a short description. On the ESP32 datasheet,
  19 of 29 figures received a non-empty description; the others are indexed through their native
  text only. Page title and native labels are indexed with it, because a small VLM reads fine
  details poorly.
- **Retrieval**: `sentence-transformers/all-MiniLM-L6-v2` embeddings in ChromaDB, fused with a
  hand-written BM25 by reciprocal rank fusion. A passage is also let through the distance threshold
  when it contains a rare uppercase identifier of the question (e.g. `HSPIQ`). Embeddings-only
  mode is available with `USE_HYBRID = False` in `src/config.py`.
- **Generation**: `llama3.2:3b` via Ollama, with a constrained prompt, temperature 0 and a cap of
  400 generated tokens.
- **Traceability**: the LLM only picks source numbers. File, page and figure name in the sources
  list are read from metadata by the code, so that list cannot contain an invented page. The
  answer text itself may still mention pages or figures written by the model, and these are not verified.

## Anti-hallucination safeguards

1. Distance threshold: if no passage is close enough, the LLM is not called. In hybrid mode, a rare
   identifier of the question can let a passage through.
2. Strict prompt with a fixed refusal sentence.
3. Citations resolved from metadata, not written by the LLM.
4. Grounding check: pin names, values with units and signal names in the answer must appear in
   the cited passage, otherwise a warning is displayed.
5. Generation cap: an answer cut at 400 tokens is flagged as truncated.

## Quick start (Windows, PowerShell)

Requires Python 3.11 or 3.12 (tested on 3.11.3) and [Ollama](https://ollama.com/download) (the app must be running).

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt

ollama pull moondream
ollama pull llama3.2:3b

# first run only: allow the embedding model download
$env:RAG_ALLOW_DOWNLOAD="1"

# put a PDF in data\raw_pdfs\, then:
python -m src.ingest

# back to offline mode
Remove-Item Env:RAG_ALLOW_DOWNLOAD

# ask questions in the terminal...
python -m src.cli

# ...or in the web interface
streamlit run src/app_streamlit.py
```

Reproduce the measurements (Ollama running):

```powershell
python -m tests.retrieval_eval                 # retrieval only, embeddings
python -m tests.retrieval_eval --mode hybrid   # retrieval only, hybrid
python -m tests.benchmark                      # end to end, embeddings
python -m tests.benchmark --hybrid             # end to end, hybrid
```

## Benchmark

### Method

27 questions on one datasheet (ESP32, 43 pages), each asked 3 times, model `llama3.2:3b`,
top-K 8, distance threshold 1.25, `LLM_MAX_TOKENS` 400, context 4096, run on 2026-10-04.
Expected answers were written from the PDF text and checked against it. Raw results, including
every answer, are in `docs/`; earlier versions of these files are in the Git history.

How the questions were built, because it matters for how to read the numbers:

| Questions | Origin |
|---|---|
| Q01 to Q10 | Initial set (text, tables, two off-topic questions) |
| Q11 to Q13 | Added after seeing the system's behavior on the first ten (figures) |
| Q14 to Q17 | Pin-function questions written before hybrid retrieval was built, already measured in embeddings mode |
| Q18 to Q22 | Pin-function questions written after hybrid retrieval was built, before any run on them |
| Q23 to Q27 | Electrical values and body text, written before the pre-registered decision below |

27 questions is a small sample: read the numbers as indicative, not as general accuracy. The benchmark
checks that expected values appear in the answer, not that they are attached to the right signal.
Q01 is partly ambiguous: the datasheet itself gives several supply ranges (2.2-3.6 V in the overview,
2.3-3.6 V for analog pins, 2.8-3.6 V for VBAT in Table 8).

### Results: embeddings vs hybrid retrieval (27 questions x 3 runs = 81 runs)

| Metric | Embeddings | Hybrid |
|---|---|---|
| Correct answers or correct refusals (runs) | 56 % (45/81) | 81 % (66/81) |
| Questions correct in all 3 runs | 15/27 | 22/27 |
| Fully correct: answer and cited page (runs) | 52 % (42/81) | 67 % (54/81) |
| Right page cited, among correct answers (runs) | 92 % (36/39) | 80 % (48/60) |
| Silent errors (wrong, no warning) | 10 % (8/81) | 10 % (8/81) |
| Flagged errors (wrong, warning shown) | 15 % (12/81) | 5 % (4/81) |
| Useless refusals (answer existed) | 20 % (16/81) | 4 % (3/81) |
| Correct answers with a warning shown | 7 % (6/81) | 22 % (18/81) |
| Questions whose verdict changed between runs | 2/27 (Q11, Q22) | 1/27 (Q24) |
| Median / max total latency (LLM called) | 0.3 s / 1.5 s | 0.4 s / 4.7 s |
| Median retrieval | 11 ms | 18 ms |

Latency is total time per question. The interfaces show the answer at once, so first-token time is not
user-visible. These were measured with the model already in memory; a cold start took about 38 s.
Repeated identical questions may benefit from caching in Ollama (not verified).

Questions not answered correctly in all 3 runs:

- Embeddings (12): Q01, Q03, Q11, Q13, Q14, Q15, Q18, Q19, Q20, Q21, Q22, Q24.
- Hybrid (5): Q01, Q11, Q15, Q21, Q24.
- No question answered correctly by embeddings was lost by hybrid.
- Q13 is counted correct in hybrid, but its answer copies the figure's labels.

Retrieval only (no LLM, results identical over two runs, measured at page level, 25 answerable questions):

| | Embeddings | Hybrid |
|---|---|---|
| Expected page in the context given to the LLM | 18/25 | 25/25 |
| All expected pages in the context | 17/25 | 24/25 |
| Off-topic questions blocked before the LLM | 2/2 | 2/2 |

### Decision rule, written before running Q23 to Q27

The rule and its clarifications are in `CLAUDE.md` (commit `4364c90`), the questions in `7fec4f5`, the
results in `b5e8d23`. Hybrid becomes the default if, on Q23 to Q27 (5 questions x 3 runs), it has at most as
many silent errors as embeddings, at least as many correct answers, and no answer slower than 10 s over the
whole run. A tie gives hybrid, by design.

| Q23 to Q27, 15 runs per mode | Embeddings | Hybrid |
|---|---|---|
| Correct answers | 12/15 | 12/15 |
| Silent errors (all on Q24) | 3/15 | 2/15 |
| Slowest answer of the whole run | 1.5 s | 4.7 s (Q21) |

The rule is satisfied, so `USE_HYBRID = True` is the default. On these five questions hybrid is not better,
only not worse: the difference is one run out of 15, and both modes retrieved an expected page for all five.
The gain comes from Q18 to Q22 (pin functions): retrieval went from 1/5 to 5/5 and correct answers from 0/5 to 4/5.
That is one family of questions on one document, and the rule was written knowing hybrid had helped on it.

### What the benchmark showed

- **Retrieval limited some answers.** For Q03 (SPICLK, SPID, SPIQ), the pin table on pages 14-15 never reached
  the LLM in embeddings mode: page 14 was absent from the 12 nearest entries and page 15 ranked 8th at a
  distance of 1.34, above the 1.25 threshold. A likely cause, not tested: the embedding model handles
  identifiers like `SPICLK` poorly. BM25 fixed the retrieval for Q03, Q14 and Q18 to Q21.
- **Retrieving the right page is not enough.** With the right context, Q15 (HSPICS0), Q21 (SPICS0) and
  Q24 (Deep-sleep power with the ULP co-processor on) still fail: the model returns the neighboring row of a table
  (Q15: GPIO13 instead of GPIO15; Q24: "25 µA @1% duty", the next row, instead of 0.15 mA). The grounding check
  cannot see it, since the value exists in the cited page.
- **Hybrid costs citation quality.** Some correct answers cite a neighboring page (Q03, Q05, Q16, Q22); the
  grounding check flags them, which explains the 22 % of correct answers shown with a warning. For Q05 the
  answer cited a generic GPIO page that the fusion had placed first, while the values were in other sources.
- **Dimensions drawn in a raster figure are not readable.** For Q11 (package dimensions), the model answered
  "1.2 mm", a value that appears neither in the indexed text of the figure nor, as far as we can tell, in the
  drawing.
- **Incomplete answers pass the check.** Q01 returned the I/O supply range as the supply range. The check
  detects values absent from the sources, not omissions.
- **Figure layout is lost.** For Q13 (blocks inside the RTC block), the native text of a vector figure keeps the
  labels but not which box contains which (likely cause, not verified).
- **No question yet shows a correct answer that depends on a drawing.** Q12 was answered from the page text, not
  from the figure. Figures are indexed and cited (see the screenshot above), but answering from a drawing is not
  demonstrated.
- **Results vary between batches even at temperature 0.** Retrieval is deterministic, so the variation comes from
  generation; the cause was not identified. Q03 gave 3 refusals in one batch, then 1 refusal and 2 flagged wrong
  answers; Q01 was a silent error in most batches and correct in one; Q11 and Q22 changed verdict within a batch.
  Differences of one question between two configurations are within this noise.

### Measured changes to the system

**Grounding check, `mm` unit.** Q11 exposed a gap: the check ignored the `mm` unit. Adding it moved Q11's wrong
answers from silent to flagged (13 questions x 3 runs, embeddings: silent errors 13 % to 8 %, flagged errors 8 % to 13 %,
correct answers unchanged at 69 %). It also produced a false alarm on Q12: the answer "2mm" is correct, but the check
reads only the cited chunk, and page 42 has "2mm" in two other indexed entries. The fix targeted a gap found on Q11 and
was measured on Q11, so it shows the fix works on that case, not that it generalizes.

**Generation cap.** Q21 produced a looping answer of 16,156 characters (about 58 s) in all three hybrid runs. After
adding `LLM_MAX_TOKENS = 400` and a truncation flag, it is cut after about 4.5 s and flagged; the maximum latency of the
hybrid benchmark dropped from 58.2 s to 4.7 s. In embeddings mode, no answer was truncated. Truncation detection relies on
`done_reason`, checked on the `ollama` Python package 0.6.3.

### Model comparison (13 questions, embeddings mode)

Measured before the generation cap and the hybrid mode, on the first 13 questions, one benchmark run for `mistral`.
Not rerun on 27 questions.

| | llama3.2:3b | mistral (7B) |
|---|---|---|
| Correct answers or refusals (questions) | 9/13 | 9/13 |
| Fully correct, answer and page (questions) | 8/13 | 8/13 |
| Wrong answer, no warning | Q01 | Q01, Q13 |
| Wrong answer, warning displayed | Q13; Q03 and Q11 in 2 runs of 3 | Q03 |
| Refusal although the answer existed | Q03 and Q11 in 1 run of 3 | Q11 |
| Median / max total latency, model loaded | 0.3 s / 1.5 s | 0.6 s / 2.8 s |

The larger model was about twice as slow and not more accurate on this set. With 13 questions and the run-to-run
variability of the 3B model, these differences are not significant. The same questions (Q01, Q03, Q11, Q13) fail with
both models, which suggests the bottleneck is upstream of the LLM, but this is not proven.

## Known limitations

- Small models read dense tables poorly: neighboring-row errors (Q15, Q21, Q24) pass the grounding check.
- The grounding check is lexical: it catches invented values and names, not real values attached to the wrong
  signal, and not omissions. It reads only the cited chunk, so a correct answer whose value sits in a neighboring
  chunk is flagged (Q12).
- The benchmark checks that expected values appear in the answer. It does not check that they are attached to the
  right signal, and a correct answer in another unit (for example "150 µA" for 0.15 mA) would be counted wrong.
- Refusal detection is a substring match: a long sourced answer that contains the refusal sentence would be replaced
  by a refusal.
- Values that appear only inside raster images depend on a small VLM and are not verified.
- The lexical gate is too broad: `gpio` appears in 6 of 150 entries, so it counts as a rare identifier and lets
  unrelated passages into the context.
- Results vary between runs for some questions, even at temperature 0.
- Page numbers are those of the PDF reader, which can differ from the printed page numbers.
- The embedding model is English-oriented, so questions should be in English for now.
- The interface texts are still partly in French.
- Tested on a single datasheet and 27 questions.

## Roadmap

- Row-level chunking of tables, to avoid neighboring-row errors (Q15, Q21, Q24)
- Ignore generic tokens such as `gpio` in the lexical gate (measure on new questions)
- Citation repair: when the cited passage lacks the answer's values but another retrieved passage contains them,
  point the citation there
- Grounding check over neighboring chunks of the same page, to remove the Q12 false alarm
- Investigate run-to-run variability
- Network audit and offline test of ingestion and hybrid mode
- English interface
- Larger benchmark, on several datasheets