# Technical RAG Assistant

An **offline, multimodal RAG assistant** for hardware and embedded engineers.
Ask questions about datasheets (text **and** figures such as pinouts and tables) and get answers
with the exact **file, page and figure name** as sources. Everything runs locally:
no cloud API, no API key, no document leaves the machine.

> Status: work in progress. A full benchmark and a web interface are on the roadmap.

## Why

Datasheets are proprietary and long. A cloud chatbot means uploading confidential documents,
and an ungrounded LLM invents pin numbers. This project keeps data local and makes every answer traceable.

## How it works

```
PDF -> text per page + figures (raster and vector) -> chunks with metadata
    -> local embeddings -> ChromaDB
Question -> embedding -> top-K passages -> local LLM -> answer with [n] citations
```

- **Extraction**: PyMuPDF reads text page by page. Vector drawings (pinouts, block diagrams) are
  detected by clustering and rendered to PNG. The native text inside each figure is kept.
- **Figures**: a local VLM (Moondream via Ollama) adds a short description. Page title and native
  labels are indexed with it, because a small VLM reads fine details poorly.
- **Retrieval**: `sentence-transformers/all-MiniLM-L6-v2` embeddings and ChromaDB.
- **Generation**: `llama3.2:3b` via Ollama, with a constrained prompt (temperature 0).
- **Traceability**: the LLM only picks source numbers. File, page and figure name are read from
  metadata by the code, so the model cannot invent a page.

## Anti-hallucination safeguards

1. Distance threshold: if no passage is close enough, the LLM is not called.
2. Strict prompt with a fixed refusal sentence.
3. Citations resolved from metadata, not written by the LLM.
4. Grounding check: pin names, values with units and signal names in the answer must appear in
   the cited sources, otherwise a warning is displayed.

## Quick start (Windows, PowerShell)

Requires Python 3.11+ and [Ollama](https://ollama.com/download).

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt

ollama pull moondream
ollama pull llama3.2:3b

# put a PDF in data\raw_pdfs\, then:
python -m src.ingest
python -m src.cli
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
- Page numbers are those of the PDF reader, which can differ from the printed page numbers.
- The embedding model is English-oriented, so questions should be in English for now.
- Tested on a single datasheet so far.

## Roadmap

- Streamlit interface showing the cited figures
- Benchmark on about 10 questions (latency and accuracy)
- Larger model comparison (3B vs 7B)
- Keyword search (BM25) alongside embeddings