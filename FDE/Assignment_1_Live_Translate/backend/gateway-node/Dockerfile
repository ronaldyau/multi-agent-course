# Gateway (Node/Express) — self-contained build (context = this folder).
# server.js serves the widget from ../../widget/translation-widget.js, so we
# recreate that layout: server.js at /app/backend/gateway-node, widget at
# /app/widget/translation-widget.js. `widget.bundled.js` is a copy of the
# provided widget/translation-widget.js (regenerate with:
#   cp ../../widget/translation-widget.js widget.bundled.js ).
FROM node:22-slim

WORKDIR /app/backend/gateway-node

# Install deps first (layer caches unless package files change).
COPY package*.json ./
RUN npm install --omit=dev

# App code, plus the widget at the path server.js expects (two levels up).
COPY server.js ./
COPY widget.bundled.js /app/widget/translation-widget.js

ENV PORT=8080
EXPOSE 8080
CMD ["node", "server.js"]
