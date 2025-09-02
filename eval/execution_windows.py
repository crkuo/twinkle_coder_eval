import io
import os
import tempfile
import platform
import contextlib
import faulthandler
import concurrent.futures
import threading
import time

from typing import Optional, Callable, Dict


# WARNING
# This program exists to execute untrusted model-generated code. Although
# it is highly unlikely that model-generated code will do something overtly
# malicious in response to this test suite, model-generated code may act
# destructively due to a lack of model capability or alignment.
# Users are strongly encouraged to sandbox this evaluation suite so that it
# does not perform destructive actions on their host or network. For more
# information on how OpenAI sandboxes its code, see the accompanying paper.
# Once you have read this disclaimer and taken appropriate precautions,
# proceed at your own risk


def check_correctness_windows(
    task_id: int,
    completion_id: int,
    solution: str,
    time_out: float = 3.0,
    tests: str = None,
) -> Dict:
    """
    Windows-compatible version of check_correctness using threading.
    Avoids multiprocessing serialization issues on Windows.
    """

    def execute_in_isolation():
        """Execute code in isolated environment."""
        try:
            # Create temporary directory for execution
            with tempfile.TemporaryDirectory() as temp_dir:
                # Change to temporary directory
                original_cwd = os.getcwd()
                os.chdir(temp_dir)

                try:
                    # Apply safety restrictions AFTER changing directory
                    apply_windows_safety_guard()

                    # Execute the solution code
                    # If additional tests are provided (e.g., for BigCodeBench), append them
                    if tests:
                        check_program = solution + "\n" + tests
                    else:
                        check_program = solution

                    exec_globals = {}
                    with redirect_io():
                        exec(check_program, exec_globals)

                    return "passed"

                except Exception as e:
                    return f"failed: {str(e)}"
                finally:
                    # Always restore original directory
                    os.chdir(original_cwd)

        except Exception as e:
            return f"failed: {str(e)}"

    # Use ThreadPoolExecutor with timeout for Windows compatibility
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(execute_in_isolation)
            try:
                result = future.result(timeout=time_out)
            except concurrent.futures.TimeoutError:
                result = "timed out"
            except Exception as e:
                result = f"failed: {str(e)}"
    except Exception as e:
        result = f"failed: {str(e)}"

    return dict(
        task_id=task_id,
        completion_id=completion_id,
        passed=result == "passed",
        result=result,
        solution=solution,
    )


@contextlib.contextmanager
def redirect_io():
    """Redirect stdout/stderr to prevent output during execution."""
    stream = WriteOnlyStringIO()
    with contextlib.redirect_stdout(stream):
        with contextlib.redirect_stderr(stream):
            with redirect_stdin(stream):
                yield


class WriteOnlyStringIO(io.StringIO):
    """StringIO that throws an exception when it's read from."""

    def read(self, *args, **kwargs):
        raise IOError

    def readline(self, *args, **kwargs):
        raise IOError

    def readlines(self, *args, **kwargs):
        raise IOError

    def readable(self, *args, **kwargs):
        """Returns True if the IO object can be read."""
        return False


class redirect_stdin(contextlib._RedirectStream):  # type: ignore
    _stream = "stdin"


def apply_windows_safety_guard(maximum_memory_bytes: Optional[int] = None):
    """
    Windows-specific safety guard that disables dangerous functions.
    Less aggressive than the original to avoid breaking execution context.
    """

    # Skip resource limits on Windows as they're not well supported
    if maximum_memory_bytes is not None and platform.system() != "Windows":
        try:
            import resource

            resource.setrlimit(
                resource.RLIMIT_AS, (maximum_memory_bytes, maximum_memory_bytes)
            )
            resource.setrlimit(
                resource.RLIMIT_DATA, (maximum_memory_bytes, maximum_memory_bytes)
            )
            if not platform.uname().system == "Darwin":
                resource.setrlimit(
                    resource.RLIMIT_STACK, (maximum_memory_bytes, maximum_memory_bytes)
                )
        except ImportError:
            pass  # resource module not available on Windows

    faulthandler.disable()

    import builtins

    builtins.exit = None
    builtins.quit = None

    # Set environment variables for safety
    import os

    os.environ["OMP_NUM_THREADS"] = "1"

    # Disable most dangerous OS functions, but keep essential ones for our context managers
    os.kill = None
    os.system = None
    os.putenv = None
    os.remove = None
    os.removedirs = None
    # Keep os.rmdir for cleanup
    os.fchdir = None
    os.setuid = None
    os.fork = None
    os.forkpty = None
    os.killpg = None
    os.rename = None
    os.renames = None
    os.truncate = None
    os.replace = None
    os.unlink = None
    os.fchmod = None
    os.fchown = None
    os.chmod = None
    os.chown = None
    os.chroot = None
    os.fchdir = None
    os.lchflags = None
    os.lchmod = None
    os.lchown = None
    # Keep os.getcwd and os.chdir for our directory management

    import shutil

    # Keep shutil.rmtree for cleanup
    shutil.move = None
    shutil.chown = None

    import subprocess

    subprocess.Popen = None  # type: ignore

    __builtins__["help"] = None

    import sys

    sys.modules["ipdb"] = None
    sys.modules["resource"] = None

    # BigCodeBench would fail if these are disabled
    # sys.modules['tkinter'] = None
    # sys.modules['joblib'] = None
    # sys.modules['psutil'] = None
