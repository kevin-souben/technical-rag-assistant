# Technical RAG Assistant

An **offline-oriented, multimodal RAG assistant** for hardware and embedded engineers.
Ask questions about datasheets (text **and** figures such as pinouts and tables) and get answers
with the exact **file, page and figure name** as sources. Models run locally through Ollama and
sentence-transformers: no cloud API, no API key.

> Status: early version. Command-line and Streamlit interfaces work; a first benchmark is included.

![Answer with the cited figure displayed](docs/demo_voltage.png)
![Refusal when the documents do not contain the answer](docs/demo_refusal.png)

## Why

Datasheets are proprietary and long. A cloud chatbot means uploading confidential documents,
and an ungrounded LLM invents pin numbers. This project keeps documents on the machine and makes every answer traceable.

Telemetry is disabled in ChromaDB and Streamlit. Internet is needed once to download the models.
After that, a CLI question and the full 13-question benchmark were run with the network disabled
and completed (Windows, Ollama running locally). The embedding library is forced into offline mode
by default; to download a model, set `RAG_ALLOW_DOWNLOAD=1`. Ingestion was not tested offline and
network traffic was not otherwise audited.

## How it works

```
PDF -> text per page + figures (raster and vector) -> chunks with metadata
    -> local embeddings -> ChromaDB
Question -> embedding -> top-K passages -> local LLM -> answer with [n] citations
```

- **Extraction**: PyMuPDF reads text page by page. Vector drawings (pinouts, block diagrams) are
  detected by clustering and rendered to PNG. The native text inside each figure is kept.
- **Figures**: a local VLM (Moondream via Ollama) adds a short description. On the ESP32 datasheet,
  19 of 29 figures received a non-empty description; the others are indexed through their native
  text only. Page title and native labels are indexed with it, because a small VLM reads fine
  details poorly.
- **Retrieval**: `sentence-transformers/all-MiniLM-L6-v2` embeddings and ChromaDB.
- **Generation**: `llama3.2:3b` via Ollama, with a constrained prompt (temperature 0).
- **Traceability**: the LLM only picks source numbers. File, page and figure name in the sources
  list are read from metadata by the code, so that list cannot contain an invented page. The
  answer text itself may still mention pages or figures written by the model, and these are not verified.

## Anti-hallucination safeguards

1. Distance threshold: if no passage is close enough, the LLM is not called.
2. Strict prompt with a fixed refusal sentence.
3. Citations resolved from metadata, not written by the LLM.
4. Grounding check: pin names, values with units and signal names in the answer must appear in
   the cited passage, otherwise a warning is displayed.

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

## Benchmark

13 questions on one datasheet (ESP32, 43 pages), each asked 3 times. Model `llama3.2:3b`,
top-K 8, distance threshold 1.25, run on 2026-10-04. Expected answers were written from the PDF
text and checked against it. 13 questions is a small sample: read these numbers as indicative,
not as general accuracy. The benchmark checks that expected values appear in the answer, not that
they are attached to the right signal. Raw results, including every answer, are in `docs/`.

Q01 is partly ambiguous: the datasheet itself gives several supply ranges (2.2-3.6 V in the
overview, 2.3-3.6 V for analog pins, 2.8-3.6 V for VBAT in Table 8).

**Results are not perfectly reproducible.** Two full runs with the same code and the same index
gave different verdicts for Q03 (3 refusals, then 1 refusal and 2 flagged wrong answers).
Retrieval was measured as identical over two runs, and the context given to the LLM was the same,
so the variability comes from generation, despite temperature 0. The cause was not identified.
The sections up to "Model comparison" were measured on the first 13 questions.

### Results per question (latest run)

| Outcome | Questions |
|---|---|
| Correct answer (or correct refusal), right page | 8 of 13 (Q12 triggers a false alarm, see below) |
| Correct answer, wrong page cited (flagged by the grounding check) | 1 of 13 (Q07) |
| Wrong answer with no warning | 1 of 13 (Q01) |
| Wrong answer with a warning displayed, in all 3 runs | 1 of 13 (Q13) |
| Verdict differs between runs (refusal in 1 run, flagged wrong answer in 2) | 2 of 13 (Q03, Q11) |

### Results per run (39 runs, grounding check v2)

| Metric | Result |
|---|---|
| Correct answers or correct refusals | 69 % (27/39) |
| Fully correct (answer and cited page, or correct refusal) | 62 % (24/39) |
| Correct answers with a warning shown (Q07, Q12) | 15 % (6/39) |
| Silent errors (wrong, no warning) | 8 % (3/39) |
| Flagged errors (wrong, warning shown) | 18 % (7/39) |
| Useless refusals (answer existed) | 5 % (2/39) |
| Correct page cited (among correct answers) | 86 % (18/21) |
| Questions whose verdict changed between runs | 2/13 (Q03, Q11) |
| Median / max total latency, model already loaded | 0.3 s / 1.5 s |
| Median retrieval | about 10 ms |

Latencies were measured with the model already in memory; a cold start took about 38 s.
Repeated identical questions may benefit from caching in Ollama (not verified).

### What the benchmark showed

- **For Q03, retrieval is a bottleneck.** The pin table on pages 14-15 never reached the LLM:
  page 14 is absent from the 12 nearest entries and page 15 ranks 8th at a distance of 1.34,
  above the 1.25 threshold. A likely cause, not tested: the embedding model handles identifiers
  like `SPICLK` poorly.
- **Dimensions drawn in a raster figure are not readable.** For Q11 (package dimensions), the model
  answered "1.2 mm", a value that appears neither in the indexed text of the figure nor, as far as
  we can tell, in the drawing. The grounding check initially missed it because its unit list did
  not include `mm`.
- **Incomplete answers pass the check.** Q01 returned the I/O supply range as the supply range.
  The check detects values absent from the sources, not omissions.
- **The grounding check catches wrong citations.** On Q07 the answer was right but cited the wrong page,
  and the check flagged it.
- **Figure layout is lost.** For Q13 (blocks inside the RTC block of the block diagram), both models
  answered wrongly. A likely cause, not verified: the native text of a vector figure keeps the labels
  but not which box contains which, and the small VLM adds nothing on this figure.
- **No benchmark question yet shows a correct answer that depends on a drawing.** Q12 was answered
  from the page text, not from the figure. Figures are indexed and cited (see the screenshot above),
  but answering from a drawing is not demonstrated.

### Check improvement: `mm` unit (v1 to v2)

Q11 exposed a gap: the grounding check ignored the `mm` unit. Adding it moved Q11's wrong
answers from silent to flagged. Accuracy did not change, only detection.

| `llama3.2:3b`, 13 questions x 3 runs | v1 | v2, first run |
|---|---|---|
| Correct answers or correct refusals | 69 % (27/39) | 69 % (27/39) |
| Silent errors | 13 % (5/39) | 8 % (3/39) |
| Flagged errors | 8 % (3/39) | 13 % (5/39) |
| Correct answers with a warning shown | 8 % (3/39), Q07 | 15 % (6/39), Q07 and Q12 |

A later v2 run gave 18 % flagged errors and 5 % useless refusals; the difference comes from
the Q03 variability above, not from the `mm` change.

The change also produced a false alarm on Q12: the answer "2mm" is correct, but the check flagged it
in every run. Page 42 contains "2mm" in two indexed entries (a text chunk and the native text
of the figure); the check only reads the cited chunk, which most likely is a neighboring one.
Net effect: better detection, one new false alarm. The fix targeted a gap found on Q11 and was
measured on Q11, so it shows the fix works on that case, not that it generalizes.

### Hybrid retrieval (embeddings + BM25), 17 questions

A hand-written BM25 is fused with the embedding ranking (reciprocal rank fusion), and a lexical
gate lets a passage through the distance threshold when it contains a rare uppercase identifier
of the question (e.g. `HSPIQ`). Off by default (`USE_HYBRID = False`). Q03 motivated it; Q14 to
Q17 were written before it was built, with no parameter tuned afterwards.

Retrieval only (no LLM, identical over two runs, measured at page level):

| | Embeddings | Hybrid |
|---|---|---|
| Answerable questions with an expected page in the LLM context | 12/15 | 15/15 |
| Off-topic questions blocked before the LLM | 2/2 | 2/2 |

End to end, `llama3.2:3b`, 17 questions x 3 runs, one batch per configuration:

| | Embeddings | Hybrid |
|---|---|---|
| Answer correct, any cited page | 11/17 | 14/17 (13/17 without Q13) |
| Answer correct and right page cited | 10/17 | 11/17 (10/17 without Q13) |
| Wrong answer, no warning | 1 (Q01) | 2 (Q01, Q15) |
| Refusal although the answer existed | 3 (Q03, Q14, Q11 in 1 run) | 1 (Q11) |
| Correct answer shown with a warning | 2 (Q07, Q12) | 5 (Q03, Q05, Q12, Q13, Q16) |

- Retrieval improved clearly, but end-to-end accuracy with the right cited page did not,
  and silent errors went from 1 to 2 questions. The hybrid mode stays off by default.
- Q13 is counted correct by the benchmark, but the answer just copies the figure's labels.
- Q03 gave the right pins but cited page 16 and added details invented from the strapping table.
- Q15: the model returned the neighboring row (GPIO13, HSPID) on the right page. The lexical check
  cannot see a real value attached to the wrong signal.
- Q05 and Q16 now cite page 28 instead of 15 (flagged by the check). Likely cause, not verified:
  the fusion changes the passage order and the model cites the wrong number.
- The lexical gate is too broad: `gpio` appears in 6 of 150 entries, so it counts as a rare identifier.

### Model comparison (same 13 questions, grounding check v2)

| | llama3.2:3b (3 runs, latest) | mistral (7B, one benchmark run) |
|---|---|---|
| Correct answers or refusals (questions) | 9/13 | 9/13 |
| Fully correct, answer and page (questions) | 8/13 | 8/13 |
| Wrong answer, no warning | Q01 | Q01, Q13 |
| Wrong answer, warning displayed | Q13; Q03 and Q11 in 2 runs of 3 | Q03 |
| Refusal although the answer existed | Q03 and Q11 in 1 run of 3 | Q11 |
| Correct answers with a warning shown (runs) | 6/39 | 6/39 |
| Median / max total latency, model loaded | 0.3 s / 1.5 s | 0.6 s / 2.8 s |

The larger model was about twice as slow and not more accurate on this set. With 13 questions and
the run-to-run variability of the 3B model, these differences are not significant. The same
questions (Q01, Q03, Q11, Q13) fail with both models, which suggests the bottleneck is upstream
of the LLM, but this is not proven.

## Known limitations

- Small models read dense tables poorly, and retrieval of identifiers looks weak (see Q03).
- Results vary between runs for some questions, even at temperature 0 (Q03, Q11).
- The grounding check is lexical: it catches invented values and names, not real values attached
  to the wrong signal, not omissions.
- The check reads only the cited chunk, so a correct answer whose value sits in a neighboring
  chunk is flagged (Q12).
- Values that appear only inside raster images depend on a small VLM and are not verified.
- Page numbers are those of the PDF reader, which can differ from the printed page numbers.
- The embedding model is English-oriented, so questions should be in English for now.
- The interface texts are still partly in French.
- Tested on a single datasheet and 13 questions. Q11 to Q13 were added after seeing the system's behavior on the first ten.
- Before the offline-mode fix, start-up waited about 23 s on retries to reach the Hugging Face Hub when the network was disabled.

## Roadmap

- Retrieval-only metric (is the expected page among the retrieved passages), deterministic and independent of the LLM
- Keyword search (BM25) alongside embeddings, for identifiers such as `SPICLK`, measured before/after
- Grounding check over neighboring chunks of the same page, to remove the Q12 false alarm
- Investigate run-to-run variability
- Network audit and offline ingestion test
- English interface
- Larger benchmark, on several datasheets
- Ignore generic tokens such as `gpio` in the lexical gate (measure on new questions)
- Row-level chunking of pin tables, to avoid neighboring-row errors