# Agentic RAG Merge Readiness Checklist

This checklist records the validation required before merging `feat/agentic-rag` into `main`.

## 1. Branch and CI

- [x] Pull request is open and mergeable.
- [x] Backend unit tests pass.
- [x] Offline agent evaluations pass.
- [x] Frontend production build passes.
- [x] Backend application and scripts compile successfully.

## 2. Real runtime validation

The validated GitHub Actions live run successfully ingested the verified DIT knowledge base and created a ChromaDB collection containing 471 chunks.

Live smoke validation passed for:

- [x] Greeting without institutional tool calls.
- [x] Factual programme retrieval using `search_dit_knowledge`.
- [x] Verified retrieval with source metadata.
- [x] Direct programme comparison using verified tooling.
- [x] Follow-up fee context with fresh verified retrieval.
- [x] Completed execution traces.

## 3. Full live evaluation suite

The full live suite passed 12/12 cases with 0 failures and a pass rate of 1.0.

Validated categories include:

- [x] Conversation routing.
- [x] DIT grounding and campus lookup.
- [x] Fee retrieval and deterministic total calculation.
- [x] Admission eligibility safety with and without a numeric applicant value.
- [x] Programme comparison.
- [x] Application-process retrieval.
- [x] Multi-step compound requests.
- [x] Follow-up memory grounding.
- [x] Hallucination-safety retrieval behaviour.

## 4. Provider/runtime resilience

- [x] Request-specific tool schemas reduce prompt overhead.
- [x] Tool results have a hard model-facing context cap.
- [x] Programme comparison has a bounded verified context and smaller response budget.
- [x] Groq rate-limit retry is handled by the production agent runtime.
- [x] The 8,000 TPM comparison failure observed during development is resolved; the final live comparison smoke case passed.
- [x] Future live CI uses a focused high-value evaluation dataset to reduce provider quota consumption while the full deterministic suite remains available offline.

## 5. Local manual product check

From the repository root:

```powershell
git checkout feat/agentic-rag
git pull origin feat/agentic-rag
cd backend
python -m scripts.ingest
python -m uvicorn app.main:app --reload
```

Open a second terminal at the repository root, then run:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` and manually confirm:

- [ ] Normal chat works.
- [ ] Programme retrieval returns understandable verified sources.
- [ ] Fee questions work and totals are calculated only from available amounts.
- [ ] Programme comparison is readable and grounded.
- [ ] Admission eligibility remains preliminary and does not claim an official DIT decision.
- [ ] Follow-up questions retain the correct programme/campus context while re-retrieving DIT facts.
- [ ] No visible regression exists in the existing chat UI.

## 6. API spot check

Optionally verify:

```text
GET  /health
POST /api/chat
GET  /api/traces/{trace_id}
DELETE /api/sessions/{session_id}
```

Confirm chat responses still provide the expected answer/source experience plus session/trace metadata used by the agentic runtime.

## 7. Merge decision

Automated CI, real Groq/Chroma smoke validation and the full 12-case live evaluation suite are complete. Keep the pull request open until the project owner completes the manual browser/UI check and explicitly approves the merge.

Recommended merge method: squash merge, so the incremental migration lands on `main` as one coherent feature change.
