FROM node:20-slim

# Install system dependencies required for canvas
RUN apt-get update && apt-get install -y \
    build-essential \
    python3 \
    python3-pip \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy the rest of the application
COPY . .

# Expose port
EXPOSE 8123

# Start command
CMD ["npm", "start"] 