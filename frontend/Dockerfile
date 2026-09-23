FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 5173

# V1 serves the Vite dev server; production builds can swap this for a static host.
CMD ["npm", "run", "dev", "--", "--host"]
