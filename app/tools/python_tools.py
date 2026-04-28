"""Python code execution tools for running Python code dynamically."""

import sys
import io
import contextlib
from typing import Any
import traceback


def execute_python(
    code: str,
    timeout: int = 30,
    capture_stdout: bool = True,
    capture_stderr: bool = True,
    globals_dict: dict[str, Any] | None = None,
    locals_dict: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute Python code and return the result.
    
    This tool allows agents to execute arbitrary Python code in a controlled environment.
    The code is executed using exec() with optional output capture.
    
    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds (note: not enforced in this basic version)
        capture_stdout: Whether to capture stdout (default: True)
        capture_stderr: Whether to capture stderr (default: True)
        globals_dict: Optional globals dictionary for execution
        locals_dict: Optional locals dictionary for execution
        
    Returns:
        Dictionary containing:
        - success: Whether the execution succeeded
        - output: Captured stdout/stderr output
        - result: The value of the last expression (if any)
        - error: Error message if execution failed
        - error_type: Type of exception if one occurred
        
    Example:
        >>> result = execute_python("print('Hello, World!')")
        >>> print(result["output"])
        
        >>> result = execute_python("x = 5\\ny = 10\\nx + y")
        >>> print(result["result"])
        
    Warning:
        This tool executes arbitrary Python code. Use with extreme caution:
        - Code runs with full access to the Python environment
        - Can access filesystem, network, system commands via subprocess/os
        - Never run untrusted code without proper sandboxing
        - Consider using restricted environments for production
    """
    # Set up default namespaces
    if globals_dict is None:
        globals_dict = {
            "__name__": "__main__",
            "__builtins__": __builtins__,
        }
    
    if locals_dict is None:
        locals_dict = {}
    
    # Capture output
    stdout_capture = io.StringIO() if capture_stdout else None
    stderr_capture = io.StringIO() if capture_stderr else None
    
    try:
        # Set up output redirection
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        if stdout_capture:
            sys.stdout = stdout_capture
        if stderr_capture:
            sys.stderr = stderr_capture
        
        try:
            # Try to evaluate as an expression first
            code_stripped = code.strip()
            
            # Check if it's a simple expression (no newlines or assignments)
            if '\n' not in code_stripped and '=' not in code_stripped:
                try:
                    result = eval(code_stripped, globals_dict, locals_dict)
                    output = stdout_capture.getvalue() if stdout_capture else ""
                    error_output = stderr_capture.getvalue() if stderr_capture else ""
                    
                    return {
                        "success": True,
                        "output": output + error_output,
                        "result": result,
                        "is_expression": True,
                    }
                except Exception:
                    pass  # Fall through to exec
            
            # Execute as statements
            exec(code, globals_dict, locals_dict)
            
            # Get captured output
            output = stdout_capture.getvalue() if stdout_capture else ""
            error_output = stderr_capture.getvalue() if stderr_capture else ""
            
            # Try to get the result of the last expression
            result = None
            if "_" in locals_dict:
                result = locals_dict["_"]
            
            return {
                "success": True,
                "output": output + error_output,
                "result": result,
                "locals": {k: v for k, v in locals_dict.items() if not k.startswith("_")},
            }
            
        finally:
            # Restore stdout/stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            
    except Exception as e:
        error_output = stderr_capture.getvalue() if stderr_capture else ""
        tb_str = traceback.format_exc()
        
        return {
            "success": False,
            "output": error_output,
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": tb_str,
        }


def execute_python_in_subprocess(
    code: str,
    timeout: int = 30,
) -> dict[str, Any]:
    """Execute Python code in a separate subprocess for better isolation.
    
    This provides better isolation than execute_python by running in a
    separate process, though it's still not fully sandboxed.
    
    Args:
        code: Python code to execute
        timeout: Maximum execution time in seconds
        
    Returns:
        Dictionary containing:
        - success: Whether the execution succeeded
        - output: Combined stdout/stderr output
        - exit_code: Process exit code
        - error: Error message if execution failed
        
    Example:
        >>> result = execute_python_in_subprocess("print('Hello from subprocess!')")
        >>> print(result["output"])
    """
    import subprocess
    import tempfile
    import os
    
    try:
        # Create a temporary file with the code
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            encoding='utf-8',
        ) as f:
            f.write(code)
            temp_path = f.name
        
        try:
            # Execute in subprocess
            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            
            output = result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            
            return {
                "success": result.returncode == 0,
                "output": output,
                "exit_code": result.returncode,
            }
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except OSError:
                pass
                
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Execution timed out after {timeout} seconds",
            "exit_code": -1,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Execution error: {str(e)}",
            "exit_code": -1,
        }


def create_restricted_globals(
    allow_builtins: list[str] | None = None,
    allow_modules: list[str] | None = None,
) -> dict[str, Any]:
    """Create a restricted globals dictionary for safer code execution.
    
    This function creates a limited execution environment by restricting
    available builtins and modules.
    
    Args:
        allow_builtins: List of allowed builtin functions (default: safe subset)
        allow_modules: List of allowed module names that can be imported
        
    Returns:
        A restricted globals dictionary suitable for use with execute_python
        
    Example:
        >>> restricted = create_restricted_globals(
        ...     allow_builtins=['len', 'str', 'int', 'float', 'list', 'dict'],
        ...     allow_modules=['math', 'random']
        ... )
        >>> result = execute_python("import math\\nmath.sqrt(16)", globals_dict=restricted)
    """
    # Default safe builtins
    if allow_builtins is None:
        allow_builtins = [
            'abs', 'all', 'any', 'bin', 'bool', 'chr', 'complex',
            'dict', 'dir', 'divmod', 'enumerate', 'filter', 'float',
            'format', 'frozenset', 'getattr', 'hasattr', 'hash',
            'hex', 'int', 'isinstance', 'issubclass', 'iter', 'len',
            'list', 'map', 'max', 'min', 'next', 'oct', 'ord', 'pow',
            'range', 'repr', 'reversed', 'round', 'set', 'slice',
            'sorted', 'str', 'sum', 'tuple', 'type', 'zip',
            'True', 'False', 'None',
        ]
    
    # Build restricted builtins
    restricted_builtins = {}
    for name in allow_builtins:
        if name in __builtins__:
            restricted_builtins[name] = __builtins__[name]
        elif hasattr(__builtins__, name):
            restricted_builtins[name] = getattr(__builtins__, name)
    
    # Create custom __import__ that restricts modules
    def restricted_import(name, *args, **kwargs):
        if allow_modules and name not in allow_modules:
            raise ImportError(f"Module '{name}' is not allowed")
        return __import__(name, *args, **kwargs)
    
    restricted_builtins['__import__'] = restricted_import
    
    return {
        "__name__": "__main__",
        "__builtins__": restricted_builtins,
    }


def python_eval(expression: str, **kwargs) -> dict[str, Any]:
    """Safely evaluate a Python expression.
    
    A simpler interface for evaluating single expressions.
    
    Args:
        expression: Python expression to evaluate
        **kwargs: Additional arguments passed to execute_python
        
    Returns:
        Same as execute_python
        
    Example:
        >>> result = python_eval("2 + 2 * 3")
        >>> print(result["result"])  # 8
    """
    return execute_python(expression, **kwargs)
