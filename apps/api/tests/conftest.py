import os
import sys

# permite `from app...` al correr pytest desde apps/api
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
