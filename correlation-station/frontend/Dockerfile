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

# Create a proper config for React SPA
RUN echo 'server { listen 3002; root /usr/share/nginx/html; index index.html; location / { try_files \$uri \$uri/ @fallback; } location @fallback { rewrite ^.*\$ /index.html last; } }' > /etc/nginx/conf.d/app.conf

EXPOSE 3002

CMD ["nginx", "-g", "daemon off;"]
