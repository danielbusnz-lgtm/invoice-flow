#!/bin/bash
# Invoice Flow - Cron runner script
# Runs the email processing pipeline every 10 minutes via crontab
#
# Crontab entry:
#   */10 * * * * /Users/danielbrooks/Projects/Personal/invoice-flow/run.sh >> /Users/danielbrooks/Projects/Personal/invoice-flow/logs/cron.log 2>&1

set -e

PROJECT_DIR="/Users/danielbrooks/Projects/Personal/invoice-flow"
PYTHON="/Users/danielbrooks/.pyenv/versions/3.11.9/bin/python"
LOG_DIR="$PROJECT_DIR/logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

echo "=========================================="
echo "Invoice Flow run: $(date)"
echo "=========================================="

cd "$PROJECT_DIR"

# Load environment variables
export $(grep -v '^#' .env | grep -v '^$' | xargs)

# Run the main processing script
$PYTHON src/main.py

echo "Completed: $(date)"
echo ""
