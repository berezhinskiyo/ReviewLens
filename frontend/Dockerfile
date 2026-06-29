# Dev-образ: Vite dev-сервер с hot-reload.
FROM node:22-alpine

WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev"]
