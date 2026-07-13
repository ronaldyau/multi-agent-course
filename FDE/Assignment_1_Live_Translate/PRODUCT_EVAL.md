# Product Evaluation — Live Translate

- **Student:** <YOUR NAME — fill before submitting>
- **Date:** 2026-07-12
- **Video demo:** <VIDEO URL — record 60–90s and paste here>
- **LLM provider / model:** Anthropic / `claude-sonnet-4-6`
- **Backend target:** `https://fde-live-translate-gw.fly.dev` (deployed) — Node gateway → Python AI service, both on Fly.io. (Benchmark numbers below were captured locally.)

## Verdict

> **Shippable for its core use case.** The backend does the hard things right: it translates English UI/e-commerce copy into natural Mexican Spanish, it **fails loud** (a provider/dependency error returns a 502 — never a silent English fallback), and its two-tier cache is genuinely excellent — a **295× speedup** on hits, **survives restarts** (SQLite), a **75% hit rate** under realistic load, and an estimated **$59/mo saving** at 500k translations. All five SLAs pass with headroom. The `/translate/batch` endpoint now translates **concurrently** (bounded semaphore, default 8): a cold batch of 12 new strings dropped from an estimated ~15s sequential to **2.7s** (~5×). The **strongest** part is the cache + fail-loud correctness. The main remaining caveat is that **bare, context-free words** can translate in the wrong sense — e.g. "Tables" → "Mesas" (furniture) instead of "Tablas" (data tables), the same context-ambiguity class as "Home" — a limitation of caching UI strings without context, not a correctness bug.

**Rubric score (from `eval/report.json`):** 70 / 70 auto (+ 30 manual)

## 1. Performance & cost (from `benchmark/bench.py`)

| Metric | Result | SLA | Pass? |
|---|---|---|---|
| Cache hit p95 | 5.3 ms | ≤ 60 ms | ✅ |
| Cache miss p95 | 1571 ms | ≤ 3500 ms | ✅ |
| Cache hit rate | 75.0 % | ≥ 60 % | ✅ |
| Throughput | 1834 req/s | ≥ 20 | ✅ |
| Error rate | 0.0 % | ≤ 1 % | ✅ |
| Cost per miss | $0.000158 | — | — |
| Monthly savings from cache | $59.23 (@ 500k/mo: $78.98 → $19.74, **75% cheaper**) | — | — |

Cold→warm speedup measured by the benchmark: **295× (miss p95 1571 ms → hit p95 5 ms).**

## 2. Live-website test

- **Site tested:** `http://www.columbia.edu/~fdc/sample.html` — a real, content-rich page not built by the student (headings, paragraphs, lists, date ranges, technical codes). Default `homedepot.com` was **not** usable via automated injection (see Resilience).
- **Translated whole page?** **Not via the visual widget overlay** — see Resilience for why. Instead, 18 real strings were scraped from the live page and sent through the **actual gateway → AI service pipeline** (`POST /translate/batch`). All 18 returned correct, natural es-MX, then re-translated at **18/18 cache hits, 0 ms**.
- **Coverage gaps:** N/A for the strings submitted (all translated). The visual whole-page DOM walk was not exercised in this run.
- **Cache on re-translate:** **18/18 cache hits, batch latencyMs = 0** on the second identical pass — the cache working exactly as designed on real-world content.
- **Resilience:** Automated console/JS injection **could not reach the local gateway** from a real external page. Two Chrome protections block it: **mixed content** (an HTTPS site cannot `fetch` `http://localhost`) and **Private Network Access** (a public site cannot call `localhost`). This is **not a backend defect** — it is precisely why the assignment ships a browser **extension**, whose background worker is exempt from these page-context rules. It resolves entirely once the gateway is deployed to HTTPS (Fly.io). No layout breakage or errors originated from the backend.
- **Screenshots:** Source page captured (English, pre-translation). Widget-overlay before/after to be captured in the video demo using the **extension** (Load unpacked → `extension/`) on `homedepot.com`.

### Sample translations (real strings from the live page)

| Original (EN) | Translation (es-MX) | Numbers/prices/codes kept? | OK? |
|---|---|---|---|
| The Washington DC Nation Mall in World War II | El National Mall de Washington DC en la Segunda Guerra Mundial | "DC" kept; "World War II" localized | ✅ |
| The New Deal in New York City 1933-1943 | El New Deal en la Ciudad de Nueva York 1933-1943 | `1933-1943` kept exactly | ✅ |
| The History of Computing at Columbia University 1890-2005 | La historia de la computación en la Universidad de Columbia 1890-2005 | `1890-2005` kept exactly | ✅ |
| HTML Syntax | Sintaxis HTML | `HTML` preserved | ✅ |
| Converting Plain Text to HTML | Convertir texto simple a HTML | `HTML` preserved | ✅ |
| Add to cart | Agregar al carrito | — (es-MX, not Castilian "añadir a la cesta") | ✅ |
| Frank da Cruz | Frank da Cruz | proper name left untouched | ✅ |
| Tables | Mesas | — | ❌ wrong sense — should be "Tablas" (data tables), not furniture |

## 3. Dimension scorecard

| Dimension | Pass / Partial / Fail | Evidence |
|---|---|---|
| Translation accuracy | **Pass** | 17/18 real strings correct and natural; one context error ("Tables"→"Mesas") |
| Mexican-Spanish register (es-MX) | **Pass** | "Agregar al carrito" (not "añadir a la cesta"); prompt anchors computadora/carro/celular, ustedes |
| Numbers / prices / codes preserved | **Pass** | Date ranges `1933-1943`, `1890-2005`, code `HTML`, and proper names all preserved verbatim |
| Page coverage | **Partial** | Backend translated 100% of submitted strings; visual whole-page overlay not exercised (extension needed) |
| Cache effectiveness | **Pass** | 18/18 hits @ 0 ms on repeat; 75% hit rate + 295× speedup in benchmark; survives restart (SQLite) |
| Latency vs SLA | **Pass** | All 5 SLAs pass with headroom (hit p95 5 ms, miss p95 1571 ms) |
| Error handling (no silent English) | **Pass** | An SDK dependency error returned HTTP 502, never a fake English fallback — fail-loud verified end-to-end |
| Resilience on a real site | **Partial** | Backend robust; page-context injection blocked by Chrome PNA/mixed-content on a *local* gateway (resolves with HTTPS deploy or the extension) |
| UX polish | **Not evaluated** | Widget UX (FAB, cache-hit badges, restore) is provided; not exercised visually this run — capture in video |

## 4. Top fixes before shipping

1. ~~**Parallelize `/translate/batch`.**~~ **Done.** Misses now run concurrently via `asyncio.gather` bounded by a semaphore (`BATCH_CONCURRENCY`, default 8); a 12-string cold batch dropped from ~15s sequential to **2.7s**. Cache hits bypass the cap.
2. **Handle context-ambiguous single words.** "Tables"→"Mesas" and the "Home" case fail because a bare UI string carries no context. Add an optional context hint (e.g. element role: nav/heading/button/body) to the prompt **and** fold it into the cache key so different senses cache separately.
3. ~~**Deploy the gateway to HTTPS (Fly.io)**~~ **Done.** Both services are live on Fly (`https://fde-live-translate-gw.fly.dev`), the cache persists on a Fly volume, and production `/health`, miss→hit, and `/stats` are all verified. This removes the mixed-content/Private-Network-Access limitation — the widget now works on real HTTPS sites (point the extension at the Fly URL), which upgrades the **Page coverage** and **Resilience on a real site** dimensions from Partial to demonstrable on homedepot.com in the video.
