"""Command line tools for executing shell commands."""

import subprocess
import os
from typing import Any


DEFAULT_TIMEOUT = 120  # Default command timeout in seconds
MAX_OUTPUT_BYTES = 100_000  # Maximum output size to capture


def execute_command(
    command: str,
    timeout: int | None = None,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
    shell: bool = True,
) -> dict[str, Any]:
    """Execute a shell command and return the output.
    
    This tool allows agents to execute arbitrary shell commands on the system.
    Use with caution - commands run with the same permissions as the agent process.
    
    Args:
        command: The shell command to execute
        timeout: Maximum time in seconds to wait for command completion (default: 120)
        cwd: Working directory for the command (default: current directory)
        env: Environment variables for the command (default: inherit from parent)
        shell: Whether to run command through shell (default: True)
        
    Returns:
        Dictionary containing:
        - success: Whether the command executed successfully (exit code 0)
        - output: Combined stdout and stderr output
        - exit_code: The command's exit code
        - command: The command that was executed
        - truncated: Whether the output was truncated
        - error: If an error occurred during execution
        
    Example:
        >>> result = execute_command("ls -la")
        >>> print(result["output"])
        >>> result = execute_command("python --version")
        >>> print(result["output"])
        
    Warning:
        This tool can execute arbitrary commands on your system. Use with caution:
        - Commands run with the same permissions as this Python process
        - Avoid running commands from untrusted sources
        - Consider using a sandboxed environment for production use
    """
    effective_timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
    
    if not command or not isinstance(command, str):
        return {
            "success": False,
            "error": "Command must be a non-empty string",
            "exit_code": 1,
        }
    
    if effective_timeout <= 0:
        return {
            "success": False,
            "error": f"Timeout must be positive, got {effective_timeout}",
            "exit_code": 1,
        }
    
    try:
        # Set up environment
        if env is None:
            # Inherit parent environment by default
            process_env = os.environ.copy()
        else:
            # Start with parent env and apply overrides
            process_env = os.environ.copy()
            process_env.update(env)
        
        # Execute the command
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=effective_timeout,
            env=process_env,
            cwd=cwd,
            check=False,  # Don't raise on non-zero exit codes
        )
        
        # Combine stdout and stderr
        output_parts = []
        if result.stdout:
            output_parts.append(result.stdout)
        if result.stderr:
            # Prefix stderr lines for clarity
            stderr_lines = result.stderr.strip().split("\n")
            output_parts.extend(f"[stderr] {line}" for line in stderr_lines)
        
        output = "\n".join(output_parts) if output_parts else "<no output>"
        
        # Check for truncation
        truncated = False
        if len(output) > MAX_OUTPUT_BYTES:
            output = output[:MAX_OUTPUT_BYTES]
            output += f"\n\n... Output truncated at {MAX_OUTPUT_BYTES} bytes."
            truncated = True
        
        # Add exit code info if non-zero
        if result.returncode != 0:
            output = f"{output.rstrip()}\n\nExit code: {result.returncode}"
        
        return {
            "success": result.returncode == 0,
            "output": output,
            "exit_code": result.returncode,
            "command": command,
            "truncated": truncated,
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Command timed out after {effective_timeout} seconds",
            "exit_code": -1,
            "command": command,
        }
    except FileNotFoundError as e:
        return {
            "success": False,
            "error": f"Command not found: {str(e)}",
            "exit_code": 127,
            "command": command,
        }
    except PermissionError as e:
        return {
            "success": False,
            "error": f"Permission denied: {str(e)}",
            "exit_code": 126,
            "command": command,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Execution error: {str(e)}",
            "exit_code": -1,
            "command": command,
        }


def run_python_script(script: str, timeout: int | None = None) -> dict[str, Any]:
    """Execute a Python script string.
    
    This is a convenience wrapper around execute_command for running Python code.
    
    Args:
        script: Python code to execute
        timeout: Maximum time in seconds (default: 120)
        
    Returns:
        Same as execute_command
        
    Example:
        >>> result = run_python_script("print('Hello, World!')")
        >>> print(result["output"])
    """
    import sys
    
    # Get the Python executable path
    python_executable = sys.executable
    
    # Write script to a temporary file and execute it
    import tempfile
    
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            temp_path = f.name
        
        try:
            result = execute_command(
                f'"{python_executable}" "{temp_path}"',
                timeout=timeout,
            )
            return result
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except OSError:
                pass
                
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to create temporary script: {str(e)}",
            "exit_code": -1,
        }


def run_command_safe(
    allowed_commands: list[str],
    command: str,
    **kwargs,
) -> dict[str, Any]:
    """Execute a command with whitelist validation.
    
    This function checks if the command starts with an allowed command prefix
    before executing it.
    
    Args:
        allowed_commands: List of allowed command prefixes (e.g., ['ls', 'cat', 'python'])
        command: The command to execute
        **kwargs: Additional arguments passed to execute_command
        
    Returns:
        Same as execute_command, or error if command not allowed
        
    Example:
        >>> result = run_command_safe(['ls', 'pwd'], 'ls -la')
        >>> result = run_command_safe(['ls', 'pwd'], 'rm -rf /')  # Will fail
    """
    # Extract the base command (first word)
    base_cmd = command.split()[0] if command.split() else ""
    
    # Check if command is allowed
    is_allowed = any(
        base_cmd == allowed or base_cmd.startswith(allowed + " ")
        for allowed in allowed_commands
    )
    
    if not is_allowed:
        return {
            "success": False,
            "error": f"Command '{base_cmd}' is not in the allowed list: {allowed_commands}",
            "exit_code": 1,
            "command": command,
        }
    
    return execute_command(command, **kwargs)
