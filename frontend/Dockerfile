# --- build stage ---
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vite inlines every VITE_-prefixed env var straight into the JS bundle
# at build time - unlike the backend's env vars, which are read at
# container startup, this one has to be known when the image is BUILT,
# not when it's run. That means changing the API URL means rebuilding
# the image, not just restarting the container with a new env var.
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# --- serve stage ---
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
