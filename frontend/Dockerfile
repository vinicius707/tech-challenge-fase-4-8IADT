FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
# `npm ci` falha no Alpine quando optional deps (emnapi) divergem do lock do macOS.
RUN npm install --no-audit --no-fund

COPY . .

ENV NEXT_TELEMETRY_DISABLED=1 \
    BACKEND_URL=http://backend:8000
# Rewrites do next.config são resolvidos no build — BACKEND_URL precisa existir antes.
RUN npm run build

ENV NODE_ENV=production
EXPOSE 3000

CMD ["npm", "start"]
