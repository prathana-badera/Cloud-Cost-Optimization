import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uvicorn
uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, log_level="info")
