# Import system modules for path management, subprocess execution, browser control, timing, and network socket checking
import sys, os, subprocess, webbrowser, time, socket, threading

# Anchor everything to the project root so the SQLite DB path resolves correctly
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)

# Add the project root directory to Python's module search path so imports work correctly
sys.path.insert(0, PROJECT_ROOT)

# Print a decorative header indicating the application is starting
print("=" * 55 + "\n  Cloud Cost Optimization Dashboard\n" + "=" * 55)

# Attempt to import all required third-party and project-specific modules
try:
    import streamlit, pandas, numpy, plotly, sklearn
    print("[OK] All modules imported")
except Exception as e:
    # If any import fails, display the error and exit with installation instructions
    print(f"[ERROR] {e}\nTry: pip install -r requirements.txt"); sys.exit(1)

# Define ports
BACKEND_PORT = 8000
DASHBOARD_PORT = 8501

# --- Start FastAPI Backend ---
print(f"\n[1/2] Starting FastAPI backend on port {BACKEND_PORT}...")
backend_proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "backend.main:app", f"--port={BACKEND_PORT}", "--host=127.0.0.1"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)

# Poll the backend port up to 20 times (with 0.5s delay) to check when it's ready
backend_ready = False
for _ in range(20):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        if s.connect_ex(("127.0.0.1", BACKEND_PORT)) == 0:
            s.close()
            backend_ready = True
            break
        s.close()
    except:
        pass
    time.sleep(0.5)

if backend_ready:
    print(f"[OK] Backend running at: http://localhost:{BACKEND_PORT}")
    print(f"     API Docs: http://localhost:{BACKEND_PORT}/docs")
else:
    print("[WARN] Backend may not be ready yet. Check for errors above.")

# --- Start Streamlit Dashboard ---
print(f"\n[2/2] Starting Streamlit dashboard on port {DASHBOARD_PORT}...")
dashboard_proc = subprocess.Popen(
    [sys.executable, "-m", "streamlit", "run", "app/dashboard.py", f"--server.port={DASHBOARD_PORT}"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)

# Poll the dashboard port up to 30 times (with 0.5s delay) to check when it's ready
for _ in range(30):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        if s.connect_ex(("127.0.0.1", DASHBOARD_PORT)) == 0:
            s.close()
            break
        s.close()
    except:
        pass
    time.sleep(0.5)

# Open the user's default web browser to the dashboard URL once the server is ready
webbrowser.open(f"http://localhost:{DASHBOARD_PORT}")
print(f"\n{'=' * 55}")
print(f"  Dashboard:  http://localhost:{DASHBOARD_PORT}")
print(f"  API:        http://localhost:{BACKEND_PORT}")
print(f"  API Docs:   http://localhost:{BACKEND_PORT}/docs")
print(f"{'=' * 55}")
print("Press Ctrl+C to stop all servers")

# Continuously print the subprocess output until the user presses Ctrl+C to terminate.
# Uses one reader thread per process: works on Windows (no select on pipes)
# and a quiet backend cannot block dashboard output.
def _pump_output(proc, tag):
    try:
        for line in iter(proc.stdout.readline, ""):
            if not line:
                break
            print(f"[{tag}] {line}", end="")
    except Exception:
        pass


threading.Thread(target=_pump_output, args=(backend_proc, "Backend"), daemon=True).start()
threading.Thread(target=_pump_output, args=(dashboard_proc, "Dashboard"), daemon=True).start()

try:
    while True:
        # If both processes are done, break
        if backend_proc.poll() is not None and dashboard_proc.poll() is not None:
            print("\nBoth servers exited.")
            break

        # If one process died unexpectedly, report it but keep supervising the other
        if backend_proc.poll() is not None:
            print("\n[WARN] Backend process exited. Dashboard is still running.")
            break
        if dashboard_proc.poll() is not None:
            print("\n[WARN] Dashboard process exited. Backend is still running.")
            break

        # Small sleep to prevent busy waiting
        time.sleep(1)
except KeyboardInterrupt:
    # Gracefully terminate both processes on keyboard interrupt
    print("\n\nStopping all servers...")
    dashboard_proc.terminate()
    backend_proc.terminate()
    dashboard_proc.wait()
    backend_proc.wait()
    print("All servers stopped.")