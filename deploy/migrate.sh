#!/bin/bash

################################################################################
# PHASE 3: Migrate
#
# Handles Django migrations and static file collection on production server
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"

source "$LIB_DIR/shared.sh"

# Validate required variables
validate_required_vars PROD_SERVER PROD_HOME VENV_PATH DEPLOY_LOG

# ===== MIGRATION EXECUTION =====

log_info "Starting migration phase..."

if [ "${DRY_RUN:-false}" = true ]; then
    log_info "[DRY-RUN] Would run Django migrations"
    log_info "[DRY-RUN] Would collect static files"
    exit 0
fi

# Run migrations on production
log_info "Running Django migrations..."

ssh_cmd "cd '$PROD_HOME/backend' && source '$VENV_PATH/bin/activate' && python manage.py migrate --noinput --verbosity=2" "Run migrations" || exit 1

log_success "Migrations completed"

# Collect static files
log_info "Collecting static files..."

ssh_cmd "cd '$PROD_HOME/backend' && source '$VENV_PATH/bin/activate' && python manage.py collectstatic --noinput --clear --verbosity=1" "Collect static" || exit 1

log_success "Static files collected"

log_success "Migration phase completed"
exit 0
