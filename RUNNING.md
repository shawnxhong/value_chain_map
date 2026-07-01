# Running VCM — Phase 0 end-to-end (the DoD)

The full stack runs on Docker Compose: **PostgreSQL (pgvector) + backend (FastAPI) + frontend
(Vite/React/Cytoscape)**. The backend container applies the Alembic migration on startup, so a clean
`docker compose up` gives you a working graph DB. This walks the Phase 0 Definition of Done:
ingest a real 10-K + a transcript → run the pipeline → confirm an edge in the UI → click it on the
graph and read its source excerpt.

> The pipeline calls the extraction/verification models (Anthropic by default) — this is **billed**.
> `--max-chunks` bounds the 10-K pass.

## 1. Configure auth

```bash
cp infra/.env.example infra/.env
# edit infra/.env and set:
#   ANTHROPIC_API_KEY=sk-ant-...
```

(Or leave it blank and mount an `ant` profile into the backend container — the SDK resolves either.)

## 2. Bring up the stack

```bash
cd infra
docker compose up -d --build          # builds backend + frontend, starts postgres, runs migration
docker compose ps                     # wait until backend is healthy
curl -s localhost:8000/api/health     # {"status":"ok", "extract_model":"claude-sonnet-4-6", ...}
```

## 3. Seed + run the pipeline

Runs the embedded HBM/GPU transcript **and** fetches NVIDIA's latest 10-K from SEC EDGAR, runs
extract → verify over their chunks, and writes `status=candidate` edges tagged `chain=hbm`:

```bash
docker compose exec backend python -m vcm.seed            # transcript + NVDA 10-K (8 chunks)
# variants:
docker compose exec backend python -m vcm.seed --no-edgar # transcript only (no network)
docker compose exec backend python -m vcm.seed --ticker AMD --max-chunks 4
docker compose exec backend python -m vcm.seed --dry-run  # run but write nothing
```

The command prints a per-document summary and the candidate queue, e.g.

```
[transcript] doc=… chunks=1 extracted=13 verified=11 unsupported=2 nodes+=9 edges_written=11 rejected=0
Candidate edges awaiting review for chain 'hbm': 11
  - SK Hynix --SUPPLIES_TO--> NVIDIA [fact/high]
  - TSMC --SUPPLIES_TO--> NVIDIA [fact/high]
  ...
```

## 4. Review + view in the UI

Open **http://localhost:5173**, enter chain `hbm`, and **Load**:

- The graph renders — **fact edges solid, inference/thesis dashed + faded**.
- Click an edge → the detail panel shows relationship, layer, confidence + reason, who-pays-whom,
  `as_of` + staleness, and the **source excerpts** (the traceability the DoD requires).
- Click **Confirm** on a candidate edge → it transitions to `confirmed` (an `audit_log` row is
  written); **Reject** hides it from the graph. (Same actions via the API below.)

Equivalent API calls:

```bash
curl -s "localhost:8000/api/graph/chain/hbm"                 # nodes + edges
curl -s "localhost:8000/api/review/candidates?chain=hbm"     # the queue (with edge ids)
curl -s -XPOST "localhost:8000/api/review/edge/<EDGE_ID>/confirm" \
     -H 'content-type: application/json' -d '{"actor":"shawn","reason":"checked filing"}'
curl -s "localhost:8000/api/evidence/<EDGE_ID>"              # excerpts + provenance
```

## Teardown

```bash
docker compose down          # keep the volume
docker compose down -v       # also drop the postgres volume (fresh DB next time)
```

## Notes / gotchas

- **SEC EDGAR** requires a descriptive `User-Agent`; the default (`VCM_EDGAR_USER_AGENT`) works for a
  demo — set your own contact in `infra/.env` for sustained use.
- **Proxy**: a host `ALL_PROXY=socks5://…` can break EDGAR/LLM calls when running the seed *outside*
  the container (needs `httpx[socks]` or `env -u ALL_PROXY`). Inside the compose network there is no
  proxy, so `docker compose exec … python -m vcm.seed` is unaffected.
- The seed transcript is embedded in `vcm/seed.py` (real transcripts are paywalled). The structured
  Phase-1 seed (`seeds/hbm_subchain.yaml`) with investability classification is separate.
