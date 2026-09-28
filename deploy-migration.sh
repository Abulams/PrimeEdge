#!/bin/bash
# Database Migration Script for Production
# Run this on your production server after deployment

cd /home/site/wwwroot/backend

# Run the subscription system migration
python migrations/setup_subscription_system.py

echo "Migration completed successfully"