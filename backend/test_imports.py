"""
Test script to check which imports are failing
"""
import sys
import traceback

print("Testing imports...")

try:
    print("1. Testing basic imports...")
    import json
    import os
    import traceback
    import time
    print("   ✓ Basic imports OK")
except Exception as e:
    print(f"   ✗ Basic imports failed: {e}")
    sys.exit(1)

try:
    print("2. Testing FastAPI imports...")
    from fastapi import FastAPI, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    print("   ✓ FastAPI imports OK")
except Exception as e:
    print(f"   ✗ FastAPI imports failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("3. Testing config import...")
    from app.core.config import settings
    print(f"   ✓ Config imported OK (DB: {settings.DATABASE_URL[:50]})")
except Exception as e:
    print(f"   ✗ Config import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("4. Testing database import...")
    from app.core.database import get_db, engine
    print("   ✓ Database imports OK")
except Exception as e:
    print(f"   ✗ Database imports failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("5. Testing parser imports...")
    print("   5a. Testing excel_parser...")
    from app.parsers.excel_parser import ExcelParser
    print("      ✓ ExcelParser OK")
    
    print("   5b. Testing word_parser...")
    from app.parsers.word_parser import WordParser
    print("      ✓ WordParser OK")
    
    print("   5c. Testing pdf_parser...")
    from app.parsers.pdf_parser import PDFParser
    print("      ✓ PDFParser OK")
except Exception as e:
    print(f"   ✗ Parser imports failed: {e}")
    traceback.print_exc()
    print("\n   Missing modules might be: camelot, pytesseract, cv2, ifcopenshell, numpy")
    sys.exit(1)

try:
    print("6. Testing extraction service import...")
    from app.services.extraction_service import ExtractionService
    print("   ✓ ExtractionService imported OK")
except Exception as e:
    print(f"   ✗ ExtractionService import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("7. Testing API router import...")
    from app.api.v1 import api_router
    print("   ✓ API router imported OK")
except Exception as e:
    print(f"   ✗ API router import failed: {e}")
    traceback.print_exc()
    sys.exit(1)

print("\nAll imports successful!")
