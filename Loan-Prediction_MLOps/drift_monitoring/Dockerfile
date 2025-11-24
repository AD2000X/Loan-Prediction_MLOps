# Dockerfile for Streamlit Drift Monitoring App
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app_v1.py .
COPY config.py .
COPY baseline.csv .
COPY latest_batch.csv .

# Create .streamlit directory for configuration
RUN mkdir -p .streamlit

# Create Streamlit config
RUN echo '\
[server]\n\
port = 8501\n\
address = "0.0.0.0"\n\
headless = true\n\
enableCORS = false\n\
\n\
[theme]\n\
primaryColor = "#FF4B4B"\n\
backgroundColor = "#FFFFFF"\n\
secondaryBackgroundColor = "#F0F2F6"\n\
textColor = "#262730"\n\
font = "sans serif"\n\
\n\
[browser]\n\
gatherUsageStats = false\n\
' > .streamlit/config.toml

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit app
CMD ["streamlit", "run", "app_v1.py", "--server.port=8501", "--server.address=0.0.0.0"]
