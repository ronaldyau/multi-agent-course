# Deploy runbook — Fly.io

Two apps, one per service (independent deploys, per the assignment's design).
The AI service holds your API key as a Fly **secret** and keeps the SQLite cache
on a **volume**; the gateway is the only app the browser needs to reach.

> Prereqs: `flyctl` installed (done), a Fly.io account with a payment method.
> App names are **globally unique** on Fly — edit the `app = "..."` line in each
> `fly.toml` to something unique to you (e.g. `fde-lt-ai-ron`, `fde-lt-gw-ron`)
> and set `primary_region` to one near you (`sjc`, `iad`, `lhr`, `syd`, ...).

Run these in your own shell (prefix with `!` here, or a normal terminal).

## 0. Log in (interactive — opens a browser)
```bash
fly auth login
```

## 1. AI service (FastAPI + cache)
```bash
cd backend/ai-service-python

# create the app from the existing fly.toml, don't deploy yet
fly launch --copy-config --no-deploy

# persistent cache volume (name must match [[mounts]].source in fly.toml)
fly volumes create translate_data --region <YOUR_REGION> --size 1

# your provider key as a secret (never baked into the image)
fly secrets set ANTHROPIC_API_KEY=sk-ant-XXXXXXXX

fly deploy
```
Verify: `curl https://<YOUR_AI_APP>.fly.dev/health` → `{"status":"ok",...}`

## 2. Gateway (Node)
The gateway build is self-contained: `widget.bundled.js` (a copy of the provided
`widget/translation-widget.js`) ships inside this folder, so Fly's build context
(the folder holding `fly.toml`) has everything it needs. If the provided widget
ever changes, regenerate the copy:
```bash
cd backend/gateway-node && cp ../../widget/translation-widget.js widget.bundled.js && cd -
```
Deploy **from inside the gateway folder** so Fly's build context is this folder
(the Dockerfile COPYs `server.js`/`widget.bundled.js` from the context root):
```bash
cd backend/gateway-node

# point the gateway at the AI app's public URL
fly secrets set AI_SERVICE_URL=https://<YOUR_AI_APP>.fly.dev

fly deploy
```
Verify (the gateway should nest the AI service's health):
```bash
curl https://<YOUR_GW_APP>.fly.dev/health
```

## 3. Smoke-test the public backend
```bash
curl -X POST https://<YOUR_GW_APP>.fly.dev/translate \
  -H 'Content-Type: application/json' \
  -d '{"text":"Add to cart","target":"es-MX"}'
# expect: {"translated":"Agregar al carrito","cached":false,...} then cached:true on repeat
```

## 4. Point the widget at production
In the Chrome extension, set the backend URL to `https://<YOUR_GW_APP>.fly.dev`
(see README Part 4). Now the widget works on real **HTTPS** sites — no more
localhost mixed-content / Private-Network-Access limitation. Record your demo here.

## Notes
- **Cache persistence:** `TRANSLATION_DB_PATH=/data/translations.db` sits on the
  volume, so your cache survives deploys — the whole point of the SQLite tier.
- **Cold starts:** `auto_stop_machines` lets idle apps scale to zero (cheap). The
  first request after idle wakes the machine (~1–2s), then it's fast.
- **Update the eval:** put `https://<YOUR_GW_APP>.fly.dev` as the Backend target
  in `PRODUCT_EVAL.md`, and re-run `benchmark/bench.py --target https://<YOUR_GW_APP>.fly.dev`
  to capture real production numbers.
