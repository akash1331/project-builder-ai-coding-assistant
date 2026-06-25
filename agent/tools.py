import pathlib
import subprocess
from datetime import datetime
from typing import Tuple

from langchain_core.tools import tool

# Each run gets its own timestamped project folder under generated_projects/, so
# completing a new prompt never overwrites a previously generated project. The
# folder name is fixed once per process (i.e. once per prompt) at import time.
GENERATED_PROJECTS_DIR = pathlib.Path.cwd() / "generated_projects"
PROJECT_ROOT = GENERATED_PROJECTS_DIR / f"project_{datetime.now():%Y%m%d_%H%M%S}"

# Create it on import so the read/list tools work even before the first write.
PROJECT_ROOT.mkdir(parents=True, exist_ok=True)


def safe_path_for_project(path: str) -> pathlib.Path:
    """Resolve ``path`` against the project root, rejecting any path that
    escapes it (e.g. via ``..``). Returns the absolute, resolved path."""
    resolved_path = (PROJECT_ROOT / path).resolve()
    project_root = PROJECT_ROOT.resolve()
    if project_root not in resolved_path.parents \
            and project_root != resolved_path.parent \
            and project_root != resolved_path:
        raise ValueError("Attempt to write outside project root")
    return resolved_path


@tool
def write_file(path: str, content: str) -> str:
    """Writes content to a file at the specified path within the project root."""
    target_path = safe_path_for_project(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as file_handle:
        file_handle.write(content)
    return f"WROTE:{target_path}"


@tool
def read_file(path: str) -> str:
    """Reads content from a file at the specified path within the project root."""
    target_path = safe_path_for_project(path)
    if not target_path.exists():
        return ""
    with open(target_path, "r", encoding="utf-8") as file_handle:
        return file_handle.read()


@tool
def get_current_directory() -> str:
    """Returns the current working directory."""
    return str(PROJECT_ROOT)


@tool
def list_files(directory: str = ".") -> str:
    """Lists all files in the specified directory within the project root."""
    target_dir = safe_path_for_project(directory)
    if not target_dir.is_dir():
        return f"ERROR: {target_dir} is not a directory"
    found_files = [
        str(file_path.relative_to(PROJECT_ROOT))
        for file_path in target_dir.glob("**/*")
        if file_path.is_file()
    ]
    return "\n".join(found_files) if found_files else "No files found."


@tool
def run_cmd(cmd: str, cwd: str = None, timeout: int = 30) -> Tuple[int, str, str]:
    """Runs a shell command in the specified directory and returns the result."""
    working_dir = safe_path_for_project(cwd) if cwd else PROJECT_ROOT
    completed = subprocess.run(
        cmd, shell=True, cwd=str(working_dir),
        capture_output=True, text=True, timeout=timeout,
    )
    return completed.returncode, completed.stdout, completed.stderr


def init_project_root():
    """Create the project root directory if it does not exist and return its path."""
    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    return str(PROJECT_ROOT)
