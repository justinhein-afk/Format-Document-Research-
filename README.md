# APA Formatter

A free web tool that turns an unformatted research paper (.docx) into an **APA 7th edition** formatted .docx.

1. Upload a Word document.
2. The app labels every paragraph (title, authors, abstract, headings, figures, tables, references, …) using
   rules plus Claude for the uncertain ones.
3. You review the labels and fix any that are wrong.
4. Download a new .docx with APA layout: 1″ margins, double spacing, Times New Roman 12 (or another APA font),
   page numbers, a student or professional title page, abstract page, five heading levels, captions above
   figures and tables, and an alphabetized reference list with hanging indents.

Images, tables, equations, hyperlinks, footnotes and inline italics/bold are copied over, not recreated.
Tracked changes are accepted and comments are removed.

## How it works

```
React (Vite) ──upload──▶ POST /api/analyze ─▶ parse ─▶ rules ─▶ Claude (uncertain blocks) ─▶ repair ─▶ labels
            ◀─ user reviews labels ─┘
            ──file + labels──▶ POST /api/render ─▶ copy blocks into a fresh APA-styled document ─▶ .docx
```

| File | Role |
|---|---|
| `backend/app/parser.py` | .docx → ordered blocks (paragraphs/tables) with formatting features; keeps each XML element |
| `backend/app/rules.py` | Deterministic labels (strong) and heuristic guesses (weak) |
| `backend/app/ai_classifier.py` | Sends compact block summaries to Claude Haiku 4.5 and gets labels back as structured output |
| `backend/app/classifier.py` | Orchestration and outline repair (one title, no skipped heading levels, …) |
| `backend/app/apa7.py` | APA styles, fonts, title case and text helpers |
| `backend/app/renderer.py` | Builds the APA document |
| `backend/app/main.py` | FastAPI endpoints, upload validation, rate limits; serves the built frontend |
| `frontend/` | Upload → review → download UI |

Nothing is written to disk: uploads are processed in memory. The browser keeps the file and sends it again
when rendering, so the server stays stateless.

## Run locally

```bash
# backend
cd backend
pip install -r requirements-dev.txt
export ANTHROPIC_API_KEY=sk-ant-...      # optional; without it only rules/heuristics are used
uvicorn app.main:app --reload --port 8000

# frontend (another terminal)
cd frontend
npm install
npm run dev                               # http://localhost:5173, proxies /api to :8000
```

Tests: `cd backend && pytest`. A messy sample paper for manual testing: `python backend/scripts/make_samples.py`
(writes `backend/tests/fixtures/messy_paper.docx`).

## Deploy

The `Dockerfile` builds the frontend and serves it from the API in a single container
(`docker build -t apa-formatter . && docker run -p 8000:8000 -e ANTHROPIC_API_KEY=... apa-formatter`).
On Render, create a Blueprint from this repo (`render.yaml`) and set `ANTHROPIC_API_KEY`.

### Keeping a free tool cheap

- Only blocks the rules are unsure about are sent to Claude, as short summaries (≤220 characters each).
  A typical paper costs a fraction of a cent with Claude Haiku 4.5.
- Uploads are capped at 10 MB / ~3,000 blocks. `ANALYZE_PER_HOUR` / `RENDER_PER_HOUR` limit requests per IP.
- Set a monthly spend limit for the API key in the Claude Console.
- `APA_CLASSIFIER_MODEL` switches the model (default `claude-haiku-4-5`).

## Limitations (v1)

- APA 7 only. Citation *content* is not rewritten (e.g. IEEE → APA); entries are only laid out and sorted.
- Text boxes, headers/footers and comments from the original are not carried over.
