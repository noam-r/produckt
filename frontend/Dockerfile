# Development target
FROM node:20-alpine as development

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN addgroup -S appuser || true && \
    adduser -D -S -G appuser appuser || true && \
    chown -R appuser:appuser /app

# Copy package files
COPY --chown=appuser:appuser package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Switch to non-root user
USER appuser

# Expose Vite dev server port
EXPOSE 5173

# Start development server with host binding
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]


# Production builder stage
FROM node:20-alpine as builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build production bundle
RUN npm run build


# Production nginx stage
FROM nginx:alpine as production

# Create non-root user for security
RUN addgroup -S appuser || true && \
    adduser -D -S -G appuser appuser || true

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Set proper permissions for nginx directories
RUN chown -R appuser:appuser /usr/share/nginx/html && \
    chown -R appuser:appuser /var/cache/nginx && \
    chown -R appuser:appuser /var/log/nginx && \
    chown -R appuser:appuser /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R appuser:appuser /var/run/nginx.pid

# Switch to non-root user
USER appuser

# Expose port 80
EXPOSE 80

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
