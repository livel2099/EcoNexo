FROM node:22-slim
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
EXPOSE 3000
# modo dev para arranque robusto en la demo local
CMD ["npm", "run", "dev"]
