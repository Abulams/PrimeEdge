"""Entry point to run seed.py as a standalone script from the backend folder."""
import sys
import os

# Add the backend directory to path so 'app' is found as a package
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.seed import seed_db

if __name__ == "__main__":
    seed_db()
