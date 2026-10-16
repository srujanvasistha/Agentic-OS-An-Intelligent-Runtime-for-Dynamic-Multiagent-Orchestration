"""Keep tests isolated from the checked-in benchmark data and local runtime DB."""
import os
import tempfile
from pathlib import Path

os.environ["AGENTOS_LLM_BACKEND"] = "mock"
os.environ["AGENTOS_DB_PATH"] = str(Path(tempfile.gettempdir()) / "agentos-pytest-tasks.sqlite3")
os.environ["AGENTOS_RESULTS_CSV"] = str(Path(tempfile.gettempdir()) / "agentos-pytest-results.csv")
