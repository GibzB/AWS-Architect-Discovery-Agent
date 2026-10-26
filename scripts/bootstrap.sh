#!/bin/bash
set -e

echo "🚀 Atlas Discovery — Project Bootstrap"
echo "======================================="
echo ""

# ──────────────────────────────────────────────────────────────
# Backend setup
# ──────────────────────────────────────────────────────────────
echo "📦 Setting up backend..."

cd apps/backend

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "   ✓ Virtual environment created"
else
    echo "   ✓ Virtual environment already exists"
fi

source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "   ✓ Python dependencies installed"

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "   ✓ .env file created (edit with your values)"
else
    echo "   ✓ .env file already exists"
fi

deactivate
cd ../..

# ──────────────────────────────────────────────────────────────
# Frontend setup
# ──────────────────────────────────────────────────────────────
echo ""
echo "📦 Setting up frontend..."

cd apps/frontend

if [ -f "package.json" ]; then
    npm install --silent
    echo "   ✓ Node dependencies installed"
else
    echo "   ⚠️  No package.json found — run frontend init first"
fi

cd ../..

# ──────────────────────────────────────────────────────────────
# Terraform init
# ──────────────────────────────────────────────────────────────
echo ""
echo "🏗️  Initialising Terraform..."

cd infra/terraform

if command -v terraform &> /dev/null; then
    terraform init -backend=false > /dev/null 2>&1
    echo "   ✓ Terraform initialised"
else
    echo "   ⚠️  Terraform not installed — skipping"
fi

cd ../..

# ──────────────────────────────────────────────────────────────
# Done
# ──────────────────────────────────────────────────────────────
echo ""
echo "✅ Bootstrap complete!"
echo ""
echo "Next steps:"
echo "  1. Edit apps/backend/.env with your AWS credentials"
echo "  2. Run: make backend    (start API server)"
echo "  3. Run: make frontend   (start React dev server)"
echo ""
