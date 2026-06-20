import sys
import os

# Ensure the project root is on sys.path so `backend.*` imports resolve
# both for pytest and for linters that read conftest.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
