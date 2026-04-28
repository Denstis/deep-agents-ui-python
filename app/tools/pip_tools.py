"""Pip package management tools for installing and managing Python packages."""

import subprocess
import sys
from typing import Any


def install_package(
    package: str,
    upgrade: bool = False,
    quiet: bool = False,
    index_url: str | None = None,
) -> dict[str, Any]:
    """Install a Python package using pip.
    
    This tool allows agents to install Python packages dynamically.
    
    Args:
        package: Package name (can include version specifier, e.g., "requests>=2.28.0")
        upgrade: Whether to upgrade if already installed (default: False)
        quiet: Whether to suppress output (default: False)
        index_url: Custom PyPI index URL (optional)
        
    Returns:
        Dictionary containing:
        - success: Whether the installation succeeded
        - output: Installation output
        - package: The package that was installed
        - error: Error message if installation failed
        
    Example:
        >>> result = install_package("requests")
        >>> print(result["success"])
        
        >>> result = install_package("numpy>=1.20", upgrade=True)
        >>> print(result["output"])
        
    Warning:
        Installing packages can modify the Python environment. Use with caution:
        - Packages are installed to the current Python environment
        - May require administrative privileges
        - Could introduce security vulnerabilities
        - Consider using virtual environments
    """
    cmd = [sys.executable, "-m", "pip", "install"]
    
    if upgrade:
        cmd.append("--upgrade")
    
    if quiet:
        cmd.append("--quiet")
    
    if index_url:
        cmd.extend(["--index-url", index_url])
    
    cmd.append(package)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout for package installation
            check=False,
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        
        return {
            "success": result.returncode == 0,
            "output": output.strip() if output else "<no output>",
            "package": package,
            "exit_code": result.returncode,
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Installation timed out after 300 seconds",
            "package": package,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Installation error: {str(e)}",
            "package": package,
        }


def uninstall_package(package: str, yes: bool = True) -> dict[str, Any]:
    """Uninstall a Python package using pip.
    
    Args:
        package: Package name to uninstall
        yes: Automatically confirm without prompting (default: True)
        
    Returns:
        Dictionary containing:
        - success: Whether the uninstallation succeeded
        - output: Uninstallation output
        - package: The package that was uninstalled
        - error: Error message if uninstallation failed
        
    Example:
        >>> result = uninstall_package("requests")
        >>> print(result["success"])
    """
    cmd = [sys.executable, "-m", "pip", "uninstall"]
    
    if yes:
        cmd.append("-y")
    
    cmd.append(package)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        
        return {
            "success": result.returncode == 0,
            "output": output.strip() if output else "<no output>",
            "package": package,
            "exit_code": result.returncode,
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Uninstallation timed out after 60 seconds",
            "package": package,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Uninstallation error: {str(e)}",
            "package": package,
        }


def list_packages(outdated: bool = False) -> dict[str, Any]:
    """List installed Python packages.
    
    Args:
        outdated: If True, only show outdated packages (default: False)
        
    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - packages: List of package dictionaries with name, version, location
        - output: Raw pip output
        - error: Error message if operation failed
        
    Example:
        >>> result = list_packages()
        >>> for pkg in result["packages"][:5]:
        ...     print(f"{pkg['name']}=={pkg['version']}")
    """
    cmd = [sys.executable, "-m", "pip", "list", "--format=json"]
    
    if outdated:
        cmd = [sys.executable, "-m", "pip", "list", "--outdated", "--format=json"]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": result.stderr or "Failed to list packages",
            }
        
        import json
        packages = json.loads(result.stdout)
        
        # Parse package information
        parsed_packages = []
        for pkg in packages:
            parsed_packages.append({
                "name": pkg.get("name", ""),
                "version": pkg.get("version", ""),
                "latest_version": pkg.get("latest_version"),  # Only for outdated
                "location": pkg.get("location"),
            })
        
        return {
            "success": True,
            "packages": parsed_packages,
            "count": len(parsed_packages),
            "output": result.stdout,
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Listing packages timed out after 60 seconds",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error listing packages: {str(e)}",
        }


def get_package_info(package: str) -> dict[str, Any]:
    """Get detailed information about an installed package.
    
    Args:
        package: Package name to get information about
        
    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - name: Package name
        - version: Installed version
        - summary: Package description
        - author: Author information
        - license: License type
        - location: Installation location
        - requires: Dependencies
        - required_by: Packages that depend on this one
        - error: Error message if operation failed
        
    Example:
        >>> result = get_package_info("requests")
        >>> print(f"Version: {result['version']}")
        >>> print(f"Summary: {result['summary']}")
    """
    cmd = [sys.executable, "-m", "pip", "show", package]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Package '{package}' not found or error: {result.stderr}",
            }
        
        # Parse pip show output
        info = {"success": True}
        current_key = None
        
        for line in result.stdout.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()
                info[key] = value
                current_key = key
            elif line.strip() and current_key:
                # Continuation of previous field
                info[current_key] += "\n" + line.strip()
        
        # Parse requires and required_by into lists
        if "requires" in info and info["requires"]:
            info["requires"] = [r.strip() for r in info["requires"].split(",")]
        else:
            info["requires"] = []
            
        if "required_by" in info and info["required_by"]:
            info["required_by"] = [r.strip() for r in info["required_by"].split(",")]
        else:
            info["required_by"] = []
        
        return info
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Getting package info timed out after 30 seconds",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error getting package info: {str(e)}",
        }


def search_packages(query: str) -> dict[str, Any]:
    """Search for packages on PyPI.
    
    Note: pip search is deprecated and may not work. This uses pip's search
    which requires XML-RPC access to PyPI.
    
    Args:
        query: Search query string
        
    Returns:
        Dictionary containing:
        - success: Whether the search succeeded
        - results: List of matching packages with name and summary
        - error: Error message if search failed
    """
    cmd = [sys.executable, "-m", "pip", "search", query]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": "pip search is deprecated. Use https://pypi.org/search/ instead.",
            }
        
        # Simple parsing of pip search output
        lines = result.stdout.strip().split("\n")
        packages = []
        
        for i, line in enumerate(lines):
            if line and not line.startswith("-"):
                parts = line.split(None, 1)
                if len(parts) >= 2:
                    packages.append({
                        "name": parts[0],
                        "summary": parts[1] if len(parts) > 1 else "",
                    })
        
        return {
            "success": True,
            "results": packages,
            "count": len(packages),
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Search error: {str(e)}",
        }


def check_requirements(requirements_file: str) -> dict[str, Any]:
    """Check if requirements from a file are satisfied.
    
    Args:
        requirements_file: Path to requirements.txt file
        
    Returns:
        Dictionary containing:
        - success: Whether all requirements are satisfied
        - missing: List of missing packages
        - installed: List of installed packages
        - error: Error message if check failed
    """
    from app.tools.filesystem import read_file
    
    # Read requirements file
    file_result = read_file(requirements_file)
    
    if not file_result.get("success"):
        return {
            "success": False,
            "error": f"Could not read requirements file: {file_result.get('error')}",
        }
    
    content = file_result["content"]
    
    # Parse requirements (simple parsing)
    required = []
    for line in content.split("\n"):
        line = line.strip()
        if line and not line.startswith("#"):
            # Extract package name (ignore version specifiers)
            pkg_name = line.split("==")[0].split(">=")[0].split("<=")[0].split("[")[0]
            if pkg_name:
                required.append(pkg_name.strip())
    
    # Get installed packages
    installed_result = list_packages()
    
    if not installed_result.get("success"):
        return {
            "success": False,
            "error": installed_result.get("error"),
        }
    
    installed_names = {pkg["name"].lower() for pkg in installed_result["packages"]}
    
    # Check which are missing
    missing = [pkg for pkg in required if pkg.lower() not in installed_names]
    installed = [pkg for pkg in required if pkg.lower() in installed_names]
    
    return {
        "success": len(missing) == 0,
        "missing": missing,
        "installed": installed,
        "total_required": len(required),
    }
