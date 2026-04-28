"""File system tools for reading, writing, and managing files."""

import os
import shutil
from pathlib import Path
from typing import Any


# Default working directory - resolved lazily to avoid blocking calls during import
DEFAULT_ROOT_DIR: str | None = None


def _get_default_root_dir() -> str:
    """Get the default root directory for file operations.
    
    Returns:
        The root directory path from AGENT_WORK_DIR env var or current working directory
    """
    global DEFAULT_ROOT_DIR
    if DEFAULT_ROOT_DIR is None:
        import os
        val = os.getenv("AGENT_WORK_DIR", os.getcwd())
        DEFAULT_ROOT_DIR = val
    return DEFAULT_ROOT_DIR


def _safe_path(path: str, root_dir: str | None = None) -> Path:
    """Safely resolve a path within the allowed root directory.
    
    Prevents path traversal attacks by ensuring the resolved path
    is within the root directory.
    
    Args:
        path: The path to resolve
        root_dir: The root directory to constrain paths to
        
    Returns:
        Resolved Path object
        
    Raises:
        ValueError: If the path is outside the allowed root directory
    """
    root = Path(root_dir or _get_default_root_dir()).resolve()
    target = Path(path).expanduser()
    
    # If path is not absolute, make it relative to root
    if not target.is_absolute():
        target = root / target
    
    target = target.resolve()
    
    # Check if the resolved path is within root
    try:
        target.relative_to(root)
    except ValueError:
        raise ValueError(
            f"Path '{path}' resolves to '{target}' which is outside "
            f"the allowed root directory '{root}'"
        )
    
    return target


def read_file(file_path: str, encoding: str = "utf-8") -> dict[str, Any]:
    """Read content from a file.
    
    Args:
        file_path: Path to the file to read
        encoding: File encoding (default: utf-8)
        
    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - content: The file content
        - file_path: The resolved file path
        - size_bytes: Size of the file in bytes
        - error: If an error occurred
        
    Example:
        >>> result = read_file("/path/to/file.txt")
        >>> print(result["content"])
    """
    try:
        safe_path = _safe_path(file_path)
        
        if not safe_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}",
            }
        
        if not safe_path.is_file():
            return {
                "success": False,
                "error": f"Not a file: {file_path}",
            }
        
        content = safe_path.read_text(encoding=encoding)
        
        return {
            "success": True,
            "content": content,
            "file_path": str(safe_path),
            "size_bytes": safe_path.stat().st_size,
        }
        
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except UnicodeDecodeError as e:
        return {
            "success": False,
            "error": f"Encoding error: {str(e)}. Try specifying a different encoding.",
        }
    except Exception as e:
        return {"success": False, "error": f"Read error: {str(e)}"}


def write_file(file_path: str, content: str, encoding: str = "utf-8", 
               create_dirs: bool = True) -> dict[str, Any]:
    """Write content to a file.
    
    Args:
        file_path: Path to the file to write
        content: Content to write to the file
        encoding: File encoding (default: utf-8)
        create_dirs: Whether to create parent directories if they don't exist
        
    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - file_path: The resolved file path
        - bytes_written: Number of bytes written
        - error: If an error occurred
        
    Example:
        >>> result = write_file("/path/to/file.txt", "Hello, World!")
        >>> print(result["bytes_written"])
    """
    try:
        safe_path = _safe_path(file_path)
        
        # Create parent directories if needed
        if create_dirs:
            safe_path.parent.mkdir(parents=True, exist_ok=True)
        
        bytes_written = safe_path.write_text(content, encoding=encoding)
        
        return {
            "success": True,
            "file_path": str(safe_path),
            "bytes_written": len(content.encode(encoding)),
        }
        
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Write error: {str(e)}"}


def delete_file(file_path: str) -> dict[str, Any]:
    """Delete a file.
    
    Args:
        file_path: Path to the file to delete
        
    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - file_path: The resolved file path
        - error: If an error occurred
        
    Example:
        >>> result = delete_file("/path/to/file.txt")
        >>> print(result["success"])
    """
    try:
        safe_path = _safe_path(file_path)
        
        if not safe_path.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}",
            }
        
        if not safe_path.is_file():
            return {
                "success": False,
                "error": f"Not a file: {file_path}",
            }
        
        safe_path.unlink()
        
        return {
            "success": True,
            "file_path": str(safe_path),
        }
        
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Delete error: {str(e)}"}


def list_directory(dir_path: str, recursive: bool = False) -> dict[str, Any]:
    """List contents of a directory.
    
    Args:
        dir_path: Path to the directory to list
        recursive: Whether to list contents recursively
        
    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - directory: The resolved directory path
        - entries: List of directory entries with name, type, size
        - error: If an error occurred
        
    Example:
        >>> result = list_directory("/path/to/dir")
        >>> for entry in result["entries"]:
        ...     print(f"{entry['type']}: {entry['name']}")
    """
    try:
        safe_path = _safe_path(dir_path)
        
        if not safe_path.exists():
            return {
                "success": False,
                "error": f"Directory not found: {dir_path}",
            }
        
        if not safe_path.is_dir():
            return {
                "success": False,
                "error": f"Not a directory: {dir_path}",
            }
        
        entries = []
        
        if recursive:
            for root, dirs, files in os.walk(safe_path):
                root_path = Path(root)
                for name in dirs:
                    full_path = root_path / name
                    rel_path = full_path.relative_to(safe_path)
                    entries.append({
                        "name": str(rel_path),
                        "type": "directory",
                        "path": str(full_path),
                    })
                for name in files:
                    full_path = root_path / name
                    rel_path = full_path.relative_to(safe_path)
                    try:
                        size = full_path.stat().st_size
                    except OSError:
                        size = 0
                    entries.append({
                        "name": str(rel_path),
                        "type": "file",
                        "path": str(full_path),
                        "size_bytes": size,
                    })
        else:
            for item in safe_path.iterdir():
                try:
                    stat = item.stat()
                    entry = {
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file",
                        "path": str(item),
                    }
                    if item.is_file():
                        entry["size_bytes"] = stat.st_size
                    entries.append(entry)
                except OSError:
                    entries.append({
                        "name": item.name,
                        "type": "unknown",
                        "path": str(item),
                        "error": "Permission denied",
                    })
        
        return {
            "success": True,
            "directory": str(safe_path),
            "entries": sorted(entries, key=lambda x: (x["type"] != "directory", x["name"].lower())),
        }
        
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"List error: {str(e)}"}


def create_directory(dir_path: str, parents: bool = True) -> dict[str, Any]:
    """Create a directory.
    
    Args:
        dir_path: Path to the directory to create
        parents: Whether to create parent directories if needed
        
    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - directory: The resolved directory path
        - created: Whether the directory was newly created
        - error: If an error occurred
        
    Example:
        >>> result = create_directory("/path/to/new/dir")
        >>> print(result["created"])
    """
    try:
        safe_path = _safe_path(dir_path)
        
        if safe_path.exists():
            if safe_path.is_dir():
                return {
                    "success": True,
                    "directory": str(safe_path),
                    "created": False,
                    "message": "Directory already exists",
                }
            else:
                return {
                    "success": False,
                    "error": f"A file with this name already exists: {dir_path}",
                }
        
        safe_path.mkdir(parents=parents, exist_ok=True)
        
        return {
            "success": True,
            "directory": str(safe_path),
            "created": True,
        }
        
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Create directory error: {str(e)}"}


def file_exists(file_path: str) -> dict[str, Any]:
    """Check if a file or directory exists.
    
    Args:
        file_path: Path to check
        
    Returns:
        Dictionary containing:
        - exists: Whether the path exists
        - is_file: Whether it's a file
        - is_directory: Whether it's a directory
        - path: The resolved path
        
    Example:
        >>> result = file_exists("/path/to/file.txt")
        >>> print(result["exists"])
    """
    try:
        safe_path = _safe_path(file_path)
        
        return {
            "exists": safe_path.exists(),
            "is_file": safe_path.is_file() if safe_path.exists() else False,
            "is_directory": safe_path.is_dir() if safe_path.exists() else False,
            "path": str(safe_path),
        }
        
    except ValueError as e:
        return {"exists": False, "error": str(e)}
    except Exception as e:
        return {"exists": False, "error": f"Error: {str(e)}"}


def get_file_info(file_path: str) -> dict[str, Any]:
    """Get detailed information about a file or directory.
    
    Args:
        file_path: Path to get information about
        
    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - path: The resolved path
        - name: File/directory name
        - type: 'file', 'directory', or 'symlink'
        - size_bytes: Size in bytes (for files)
        - created: Creation time
        - modified: Last modification time
        - accessed: Last access time
        - permissions: File permissions (octal)
        - error: If an error occurred
        
    Example:
        >>> result = get_file_info("/path/to/file.txt")
        >>> print(f"Size: {result['size_bytes']} bytes")
    """
    try:
        safe_path = _safe_path(file_path)
        
        if not safe_path.exists():
            return {
                "success": False,
                "error": f"Path not found: {file_path}",
            }
        
        stat = safe_path.stat()
        
        info = {
            "success": True,
            "path": str(safe_path),
            "name": safe_path.name,
            "type": "symlink" if safe_path.is_symlink() else ("directory" if safe_path.is_dir() else "file"),
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "accessed": stat.st_atime,
            "permissions": oct(stat.st_mode)[-3:],
        }
        
        if safe_path.is_file():
            info["size_bytes"] = stat.st_size
        
        return info
        
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Info error: {str(e)}"}


def copy_file(source_path: str, dest_path: str) -> dict[str, Any]:
    """Copy a file from source to destination.
    
    Args:
        source_path: Path to the source file
        dest_path: Path to the destination
        
    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - source: The resolved source path
        - destination: The resolved destination path
        - error: If an error occurred
    """
    try:
        safe_source = _safe_path(source_path)
        safe_dest = _safe_path(dest_path)
        
        if not safe_source.exists():
            return {"success": False, "error": f"Source not found: {source_path}"}
        
        if not safe_source.is_file():
            return {"success": False, "error": f"Source is not a file: {source_path}"}
        
        # Create parent directories if needed
        safe_dest.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(safe_source, safe_dest)
        
        return {
            "success": True,
            "source": str(safe_source),
            "destination": str(safe_dest),
        }
        
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Copy error: {str(e)}"}


def move_file(source_path: str, dest_path: str) -> dict[str, Any]:
    """Move a file from source to destination.
    
    Args:
        source_path: Path to the source file
        dest_path: Path to the destination
        
    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - source: The resolved source path
        - destination: The resolved destination path
        - error: If an error occurred
    """
    try:
        safe_source = _safe_path(source_path)
        safe_dest = _safe_path(dest_path)
        
        if not safe_source.exists():
            return {"success": False, "error": f"Source not found: {source_path}"}
        
        # Create parent directories if needed
        safe_dest.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.move(safe_source, safe_dest)
        
        return {
            "success": True,
            "source": str(safe_source),
            "destination": str(safe_dest),
        }
        
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Move error: {str(e)}"}


# Aliases for convenience
list_files = list_directory
