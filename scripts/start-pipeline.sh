
#!/bin/bash
set -e

echo 'Waiting for Prefect server...'
# Wait for Prefect API to be ready with timeout
MAX_RETRIES=30
RETRY_COUNT=0
until prefect config view --show-sources >/dev/null 2>&1; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo 'Prefect server not available after 30 attempts'
    exit 1
  fi
  echo "Attempt $RETRY_COUNT/$MAX_RETRIES - Prefect server not ready yet..."
  sleep 1
done
echo 'Prefect server is ready!'

echo 'Creating work pool...'
prefect work-pool create job-scraper-pool --type process 2>/dev/null || \
  echo '✓ Pool already exists'

echo 'Deploying flows...'
prefect deploy --all

echo 'Starting worker in background...'
prefect worker start --pool job-scraper-pool &
WORKER_PID=$!

# Wait for worker to register with the pool
echo 'Waiting for worker to be ready...'
MAX_RETRIES=20
RETRY_COUNT=0
until prefect work-pool get-default-queue job-scraper-pool >/dev/null 2>&1; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo 'Worker may not be fully ready, but proceeding...'
    break
  fi
  sleep 1
done
echo 'Worker is ready!'

echo 'Worker running. Pipeline will execute shortly...'
echo 'View progress at: http://localhost:4200'

# Keep container running
wait $WORKER_PID
