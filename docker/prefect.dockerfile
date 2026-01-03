FROM prefecthq/prefect:3.4.25-python3.12

# Install curl for healthcheck
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Expose Prefect server port
EXPOSE 4200

# Start Prefect server
CMD ["prefect", "server", "start", "--no-services"]
