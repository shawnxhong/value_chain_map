FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

# Dev server (Phase 0). A production build (vite build + static serve) comes later.
CMD ["npm", "run", "dev"]
