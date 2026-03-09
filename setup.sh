#!/bin/bash
# ============================================================
# LeaveDesk — Eye Hospital HR System
# Setup Script
# ============================================================

echo "=========================================="
echo "  LeaveDesk HR System — Setup"
echo "=========================================="
echo ""

# Check Python
python3 --version 2>/dev/null || { echo "ERROR: Python 3 not found."; exit 1; }

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run migrations
echo ""
echo "🗄️  Setting up database..."
python manage.py makemigrations accounts
python manage.py makemigrations leaves
python manage.py makemigrations dashboard
python manage.py migrate

# Seed demo data
echo ""
echo "🌱 Loading demo data..."
python manage.py seed_data

# Create superuser prompt
echo ""
echo "=========================================="
echo "✅ Setup complete!"
echo "=========================================="
echo ""
echo "📋 Demo Login Credentials:"
echo "  HR Admin:     hr_admin / hospital2024"
echo "  Line Manager: dr_fon   / hospital2024"
echo "  Employee:     nurse_mary / hospital2024"
echo ""
echo "▶  Start server: python manage.py runserver"
echo "   Then open:    http://127.0.0.1:8000"
echo ""
