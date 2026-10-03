# Technical RAG Assistant

An **offline, multimodal RAG assistant** for hardware and embedded engineers.
Ask questions about datasheets (text **and** figures such as pinouts and tables) and get answers
with the exact **file, page and figure name** as sources. Everything runs locally:
no cloud API, no API key, no document leaves the machine.

> Status: early version. Command-line and Streamlit interfaces work; a full benchmark is in progress.

![Answer with the cited figure displayed](docs/demo_voltage.png)
![Refusal when the documents do not contain the answer](docs/demo_refusal.png)

## Why

Datasheets are proprietary and long. A cloud chatbot means uploading confidential documents,
and an ungrounded LLM invents pin numbers. This project keeps data local and makes every answer traceable.

Telemetry is disabled in ChromaDB and Streamlit. Internet is used only to download the models once.

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
- **Traceability**: the LLM only picks source numbers. File, page and figure name are read from
  metadata by the code, so a page number cannot be invented. The model can still cite the wrong
  passage, which is why the grounding check below exists.

## Anti-hallucination safeguards

1. Distance threshold: if no passage is close enough, the LLM is not called.
2. Strict prompt with a fixed refusal sentence.
3. Citations resolved from metadata, not written by the LLM.
4. Grounding check: pin names, values with units and signal names in the answer must appear in
   the cited sources, otherwise a warning is displayed.

## Quick start (Windows, PowerShell)

Requires Python 3.11 or 3.12 (tested on 3.11.3) and [Ollama](https://ollama.com/download).

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt

ollama pull moondream
ollama pull llama3.2:3b

# put a PDF in data\raw_pdfs\, then:
python -m src.ingest

# ask questions in the terminal...
python -m src.cli

# ...or in the web interface
streamlit run src/app_streamlit.py
```

Internet is needed only once, to download the models.

## Measured so far

Informal measurements on one machine, one PDF (ESP32 datasheet, 43 pages). A proper benchmark will replace them.

| Step | Result |
|---|---|
| Extraction + chunking | about 1.1 s (121 text chunks, 29 figures) |
| Indexing 150 entries | about 4 s |
| Retrieval | about 0.01 s |
| LLM first token, model already loaded | about 0.4 to 7 s |
| LLM first load | about 38 s |

## Known limitations

- Small models read dense tables poorly. Example: asked which pins carry `SPICLK`, `SPID` and `SPIQ`,
  the 3B model gave wrong pins. The signal names were missing from the cited page, so the
  grounding check displayed a warning. Correct answer in the document: GPIO6, GPIO8 and GPIO7.
- The grounding check is lexical: it catches invented values and names, not real values
  attached to the wrong signal.
- Answers can vary between runs, even at temperature 0. The same SPI question gave a wrong
  answer with a warning in the CLI and a clean refusal in the web interface.
- Answers sometimes include related but off-topic parameters (for example input voltage
  levels when asked for the supply range).
- Page numbers are those of the PDF reader, which can differ from the printed page numbers.
- The embedding model is English-oriented, so questions should be in English for now.
- Tested on a single datasheet so far.

## Roadmap

- Benchmark on about 10 questions, each asked 3 times (latency, accuracy, run-to-run variability)
- Larger model comparison (3B vs 7B)
- Keyword search (BM25) alongside embeddings