FROM node:20-alpine

WORKDIR /app

ARG HTTP_PROXY
ARG HTTPS_PROXY
ARG NO_PROXY
ARG http_proxy
ARG https_proxy
ARG no_proxy

COPY package.json ./
RUN npm_config_proxy="${HTTP_PROXY}" npm_config_https_proxy="${HTTPS_PROXY}" npm install

COPY . .

EXPOSE 5173

# Dev server (Phase 0). A production build (vite build + static serve) comes later.
CMD ["npm", "run", "dev"]
