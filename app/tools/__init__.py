"""Tools module for Deep Agents.

This module provides various tools for agents including:
- Internet tools (web search, URL fetch)
- File system tools (read, write, list, delete files)
- Command line tools (execute shell commands)
- Python tools (execute Python code)
- Pip tools (install/manage packages)
- Network tools (ping, port scan, HTTP requests)
"""

from app.tools.internet import web_search, fetch_url, duckduckgo_search
from app.tools.filesystem import (
    read_file,
    write_file,
    list_files,
    delete_file,
    create_directory,
    list_directory,
    file_exists,
    get_file_info,
    copy_file,
    move_file,
)
from app.tools.command_line import execute_command, run_python_script, run_command_safe
from app.tools.python_tools import (
    execute_python,
    execute_python_in_subprocess,
    create_restricted_globals,
    python_eval,
)
from app.tools.pip_tools import (
    install_package,
    list_packages,
    uninstall_package,
    get_package_info,
    check_requirements,
)
from app.tools.network import (
    ping_host,
    http_request,
    get_network_info,
    port_scan,
    resolve_hostname,
)

__all__ = [
    # Internet tools
    "web_search",
    "fetch_url",
    "duckduckgo_search",
    # File system tools
    "read_file",
    "write_file",
    "list_files",
    "delete_file",
    "create_directory",
    "list_directory",
    "file_exists",
    "get_file_info",
    "copy_file",
    "move_file",
    # Command line tools
    "execute_command",
    "run_python_script",
    "run_command_safe",
    # Python tools
    "execute_python",
    "execute_python_in_subprocess",
    "create_restricted_globals",
    "python_eval",
    # Pip tools
    "install_package",
    "list_packages",
    "uninstall_package",
    "get_package_info",
    "check_requirements",
    # Network tools
    "ping_host",
    "http_request",
    "get_network_info",
    "port_scan",
    "resolve_hostname",
]
