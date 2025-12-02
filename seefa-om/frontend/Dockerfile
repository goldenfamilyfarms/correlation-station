# Build stage
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage - serve static files only
FROM nginx:alpine

# Copy built files to nginx
COPY --from=build /app/dist /usr/share/nginx/html

# Remove default nginx config since host will handle routing
RUN rm /etc/nginx/conf.d/default.conf

# Create a simple config that just serves static files
RUN echo 'server { listen 3002; location / { root /usr/share/nginx/html; try_files \$uri \$uri/ /index.html; } }' > /etc/nginx/conf.d/app.conf

EXPOSE 3002

CMD ["nginx", "-g", "daemon off;"]
