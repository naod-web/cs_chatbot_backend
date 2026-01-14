#!/bin/bash
echo "=== Setting up Chatbot with Python 3.11.14 ==="

# Remove old environment if exists
if [ -d "flask_env" ]; then
    echo "Removing old virtual environment..."
    rm -rf flask_env
fi

# Create virtual environment with Python 3.11
echo "Creating virtual environment with Python 3.11..."
python3.11 -m venv flask_env

# Activate
echo "Activating environment..."
source flask_env/bin/activate

echo "Python: $(python --version)"
echo "Pip: $(pip --version)"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Create full requirements.txt
echo "Creating requirements.txt..."
cat > requirements.txt << 'REQEOF'
Flask==3.0.0
Flask-CORS==4.0.0
python-dotenv==1.0.0
Werkzeug==3.0.1
pyodbc==5.0.1
pymssql==2.2.7
scikit-learn==1.3.2
numpy==1.24.3
pandas==2.0.3
scipy==1.11.4
joblib==1.3.2
sentence-transformers==2.2.2
openpyxl==3.1.2
rapidfuzz==3.6.1
REQEOF

# Install all packages
echo "Installing packages (this will take a few minutes)..."
pip install -r requirements.txt

# Verify installations
echo ""
echo "=== Verification ==="
python -c "import flask; print(f'✓ Flask {flask.__version__}')" 2>/dev/null || echo "✗ Flask not installed"
python -c "import sklearn; print(f'✓ scikit-learn {sklearn.__version__}')" 2>/dev/null || echo "✗ scikit-learn not installed"
python -c "import numpy; print(f'✓ numpy {numpy.__version__}')" 2>/dev/null || echo "✗ numpy not installed"
python -c "import pandas; print(f'✓ pandas {pandas.__version__}')" 2>/dev/null || echo "✗ pandas not installed"
python -c "import pymssql; print('✓ pymssql imported')" 2>/dev/null || echo "✗ pymssql not installed"

echo ""
echo "=== SETUP COMPLETE! ==="
echo "Virtual environment: flask_env"
echo "To activate: source flask_env/bin/activate"
echo "To run: python run.py"
