import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from streamlit.web import cli as stcli
sys.argv = ["streamlit", "run", "app/dashboard.py", "--server.port=8501", "--server.address=127.0.0.1"]
sys.exit(stcli.main())
