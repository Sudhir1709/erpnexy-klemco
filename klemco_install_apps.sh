#!/bin/bash
# Run this inside the backend container to install all Klemco apps
# Usage: docker exec frappe_docker-backend-1 bash /home/frappe/frappe-bench/klemco_install_apps.sh

set -e
cd /home/frappe/frappe-bench
source env/bin/activate

echo "Installing India Compliance (version-16)..."
bench get-app india_compliance https://github.com/resilient-tech/india-compliance --branch version-16

echo "Installing on site..."
bench --site mysite.localhost install-app india_compliance

echo "Clearing cache..."
bench --site mysite.localhost clear-cache

echo ""
bench --site mysite.localhost list-apps
echo ""
echo "✅ All apps installed!"
