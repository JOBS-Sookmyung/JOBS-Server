import os, sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))

from fastapi import HTTPException
from config import FILE_DIR
import json, tabula, pandas as pd

def echo(detail = None, status_code: int = None) -> any:
    if status_code != None:
        detail = HTTPException(status_code, detail)
    print(detail)
    return detail

def clean_files():
    print("Clean files started")
    if os.path.exists(FILE_DIR):
        for f in os.scandir(FILE_DIR):
            os.remove(f.path)
    print("Clean files completed")
