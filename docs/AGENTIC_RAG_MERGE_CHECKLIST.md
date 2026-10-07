# Agentic RAG Merge Readiness Checklist

This checklist must be completed before merging `feat/agentic-rag` into `main`.

## 1. Branch and CI

- [ ] Pull request is open and mergeable.
- [ ] Backend unit tests pass.
- [ ] Offline agent evaluations pass.
- [ ] Frontend production build passes.
- [ ] Backend application and scripts compile successfully.

## 2. Local environment preflight

From the repository root:

```powershell
git checkout feat/agentic-rag
git pull origin feat/agentic-rag
cd backend
```

Confirm the Groq key is available in the environment or `.env` file:

```powershell
$env:GROQ_API_KEY
```

Install backend dependencies if needed:

```powershell
python -m pip install -r requirements.txt
```

Ingest the verified DIT knowledge base if the local ChromaDB collection has not been prepared:

```powershell
python -m scripts.ingest
```

## 3. Live smoke tests

Run:

```powershell
python scripts/smoke_test_agent.py
```

The smoke suite must confirm all of the following:

- [ ] A greeting can be answered without institutional tools.
- [ ] A factual programme question uses `search_dit_knowledge`.
- [ ] Verified factual retrieval returns at least one source.
- [ ] A direct programme comparison uses `compare_dit_programmes`.
- [ ] A follow-up question such as `What about the fees?` keeps programme context.
- [ ] The follow-up still performs fresh verified retrieval rather than trusting memory as institutional truth.
- [ ] Every run produces a completed execution trace.

## 4. Live evaluation suite

Run:

```powershell
python scripts/evaluate_agent.py --mode live
```

Review every failed case instead of lowering the expected behaviour to make the suite pass.

Required before merge:

- [ ] No unsafe final-admission claim is produced.
- [ ] Eligibility checks retrieve verified requirements first.
- [ ] Programme comparisons use verified data.
- [ ] Factual DIT answers are grounded with sources where the dataset expects sources.
- [ ] Compound requests use the expected tools and task decomposition.

## 5. API smoke test

Start FastAPI:

```powershell
python -m uvicorn app.main:app --reload
```

Verify:

```text
GET  /health
POST /api/chat
GET  /api/traces/{trace_id}
DELETE /api/sessions/{session_id}
```

For `/api/chat`, confirm the response includes:

```json
{
  "answer": "...",
  "sources": [],
  "session_id": "...",
  "trace_id": "..."
}
```

Then retrieve the returned trace ID and confirm the trace does not expose full user messages, retrieved document text, tool arguments, or full final answers.

## 6. Frontend behaviour

- [ ] Existing chat UI still sends messages successfully.
- [ ] `session_id` is reused during the same browser session.
- [ ] Starting a fresh chat creates a new session.
- [ ] Sources still render correctly.
- [ ] No visible regression is caused by the additional `trace_id` response field.

## 7. Merge decision

Merge only when all required automated checks are green and the live Groq/Chroma smoke tests have passed.

Recommended merge method: squash merge, so the large incremental migration lands on `main` as one coherent feature change.
