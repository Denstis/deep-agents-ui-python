"""Network tools for ping, HTTP requests, and network diagnostics."""

import socket
import subprocess
from typing import Any
from urllib.parse import urlparse


def ping_host(host: str, count: int = 4, timeout: int = 10) -> dict[str, Any]:
    """Ping a host to check connectivity.
    
    Args:
        host: Hostname or IP address to ping
        count: Number of ping packets to send (default: 4)
        timeout: Timeout in seconds (default: 10)
        
    Returns:
        Dictionary containing:
        - success: Whether the ping succeeded
        - host: The target host
        - reachable: Whether the host is reachable
        - packets_sent: Number of packets sent
        - packets_received: Number of packets received
        - packet_loss: Percentage of packet loss
        - min_rtt: Minimum round-trip time in ms
        - avg_rtt: Average round-trip time in ms
        - max_rtt: Maximum round-trip time in ms
        - output: Raw ping output
        - error: Error message if ping failed
        
    Example:
        >>> result = ping_host("google.com")
        >>> print(f"Reachable: {result['reachable']}")
        >>> print(f"Packet loss: {result['packet_loss']}%")
    """
    # Determine ping command based on OS
    import platform
    
    system = platform.system().lower()
    
    if system == "windows":
        cmd = ["ping", "-n", str(count), "-w", str(timeout * 1000), host]
    else:
        cmd = ["ping", "-c", str(count), "-W", str(timeout), host]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 5,  # Extra buffer
            check=False,
        )
        
        output = result.stdout + result.stderr
        reachable = result.returncode == 0
        
        # Parse ping statistics (simplified parsing)
        stats = {
            "success": reachable,
            "host": host,
            "reachable": reachable,
            "packets_sent": count,
            "packets_received": 0,
            "packet_loss": 100.0 if not reachable else 0.0,
            "output": output.strip(),
        }
        
        # Try to extract RTT values (Linux/Mac format)
        if "rtt" in output.lower() or "round-trip" in output.lower():
            import re
            
            # Look for rtt min/avg/max/mdev pattern
            rtt_match = re.search(
                r"(?:rtt|round-trip)\s+min/avg/max(?:/mdev|/stddev)?\s*=\s*"
                r"([\d.]+)/([\d.]+)/([\d.]+)",
                output,
                re.IGNORECASE,
            )
            
            if rtt_match:
                stats["min_rtt"] = float(rtt_match.group(1))
                stats["avg_rtt"] = float(rtt_match.group(2))
                stats["max_rtt"] = float(rtt_match.group(3))
        
        # Try to extract packet loss
        loss_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*packet\s*loss", output, re.IGNORECASE)
        if loss_match:
            stats["packet_loss"] = float(loss_match.group(1))
        
        # Try to extract packets received
        recv_match = re.search(r"(\d+)\s+packets?\s+transmitted.*?(\d+)\s+received", output, re.IGNORECASE)
        if recv_match:
            stats["packets_sent"] = int(recv_match.group(1))
            stats["packets_received"] = int(recv_match.group(2))
        
        return stats
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "host": host,
            "reachable": False,
            "error": f"Ping timed out after {timeout + 5} seconds",
        }
    except FileNotFoundError:
        return {
            "success": False,
            "host": host,
            "reachable": False,
            "error": "ping command not found",
        }
    except Exception as e:
        return {
            "success": False,
            "host": host,
            "reachable": False,
            "error": f"Ping error: {str(e)}",
        }


def http_request(
    url: str,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    data: str | dict | None = None,
    timeout: int = 30,
    follow_redirects: bool = True,
) -> dict[str, Any]:
    """Make an HTTP request to a URL.
    
    Args:
        url: The URL to request
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        headers: Optional HTTP headers dictionary
        data: Request body (string or dict for JSON)
        timeout: Request timeout in seconds (default: 30)
        follow_redirects: Whether to follow redirects (default: True)
        
    Returns:
        Dictionary containing:
        - success: Whether the request succeeded
        - status_code: HTTP status code
        - headers: Response headers
        - content: Response body
        - elapsed_ms: Request time in milliseconds
        - error: Error message if request failed
        
    Example:
        >>> result = http_request("https://api.github.com/users/github")
        >>> print(f"Status: {result['status_code']}")
        >>> print(result['content'][:200])
    """
    try:
        import requests
    except ImportError:
        return {
            "success": False,
            "error": "requests package not installed. Install with: pip install requests",
        }
    
    # Validate URL
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return {
            "success": False,
            "error": f"Invalid URL scheme: {parsed.scheme}. Must be http or https.",
        }
    
    try:
        # Prepare request
        kwargs = {
            "timeout": timeout,
            "allow_redirects": follow_redirects,
        }
        
        if headers:
            kwargs["headers"] = headers
        
        if isinstance(data, dict):
            kwargs["json"] = data
        elif data:
            kwargs["data"] = data
        
        # Make request
        response = requests.request(method.upper(), url, **kwargs)
        
        return {
            "success": 200 <= response.status_code < 400,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "content": response.text,
            "elapsed_ms": int(response.elapsed.total_seconds() * 1000),
            "url": str(response.url),
        }
        
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": f"Request timed out after {timeout} seconds",
        }
    except requests.exceptions.ConnectionError as e:
        return {
            "success": False,
            "error": f"Connection error: {str(e)}",
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"HTTP request error: {str(e)}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Request error: {str(e)}",
        }


def get_network_info() -> dict[str, Any]:
    """Get information about the current network configuration.
    
    Returns:
        Dictionary containing:
        - hostname: System hostname
        - ip_addresses: List of local IP addresses
        - default_gateway: Default gateway IP (if detectable)
        - dns_servers: DNS server addresses (if detectable)
        - interfaces: Network interface information
        
    Example:
        >>> result = get_network_info()
        >>> print(f"Hostname: {result['hostname']}")
        >>> print(f"IPs: {result['ip_addresses']}")
    """
    import platform
    
    info = {
        "success": True,
        "hostname": socket.gethostname(),
        "ip_addresses": [],
        "interfaces": {},
    }
    
    # Get all IP addresses
    try:
        # Get primary IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Doesn't need to be reachable
            s.connect(("10.255.255.255", 1))
            info["primary_ip"] = s.getsockname()[0]
        except Exception:
            info["primary_ip"] = "127.0.0.1"
        finally:
            s.close()
    except Exception:
        pass
    
    # Get all interface addresses
    try:
        addrs = socket.getaddrinfo(info["hostname"], None)
        ips = set()
        for addr in addrs:
            ip = addr[4][0]
            if ip != "127.0.0.1" and not ip.startswith("::"):
                ips.add(ip)
        info["ip_addresses"] = list(ips)
    except Exception:
        pass
    
    # Try to get more detailed interface info
    system = platform.system().lower()
    
    try:
        if system == "windows":
            cmd = ["ipconfig", "/all"]
        else:
            cmd = ["ifconfig"] if system == "darwin" else ["ip", "addr"]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        
        if result.returncode == 0:
            info["interface_output"] = result.stdout.strip()
    except Exception:
        pass
    
    # Try to get DNS servers
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        info["dns_servers"] = resolver.nameservers
    except ImportError:
        # Fallback: read from resolv.conf on Unix
        try:
            with open("/etc/resolv.conf") as f:
                dns_servers = []
                for line in f:
                    if line.strip().startswith("nameserver"):
                        parts = line.split()
                        if len(parts) > 1:
                            dns_servers.append(parts[1])
                if dns_servers:
                    info["dns_servers"] = dns_servers
        except Exception:
            pass
    except Exception:
        pass
    
    return info


def port_scan(host: str, ports: list[int] | None = None, timeout: float = 1.0) -> dict[str, Any]:
    """Scan ports on a host to check which are open.
    
    Args:
        host: Hostname or IP to scan
        ports: List of ports to scan (default: common ports [21, 22, 23, 25, 80, 443, 8080])
        timeout: Timeout per port in seconds (default: 1.0)
        
    Returns:
        Dictionary containing:
        - success: Whether the scan completed
        - host: Target host
        - open_ports: List of open ports with service names
        - closed_ports: List of closed/filtered ports
        - scanned: Total number of ports scanned
        
    Example:
        >>> result = port_scan("localhost", ports=[22, 80, 443])
        >>> print(f"Open ports: {result['open_ports']}")
    """
    if ports is None:
        ports = [21, 22, 23, 25, 53, 80, 110, 143, 443, 993, 995, 3306, 3389, 5432, 8080, 8443]
    
    # Common service names
    services = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
        80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 993: "IMAPS",
        995: "POP3S", 3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL",
        8080: "HTTP-Alt", 8443: "HTTPS-Alt",
    }
    
    open_ports = []
    closed_ports = []
    
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                open_ports.append({
                    "port": port,
                    "service": services.get(port, "unknown"),
                })
            else:
                closed_ports.append(port)
                
        except Exception:
            closed_ports.append(port)
    
    return {
        "success": True,
        "host": host,
        "open_ports": open_ports,
        "closed_ports": closed_ports,
        "scanned": len(ports),
    }


def resolve_hostname(hostname: str) -> dict[str, Any]:
    """Resolve a hostname to IP addresses.
    
    Args:
        hostname: Hostname to resolve
        
    Returns:
        Dictionary containing:
        - success: Whether resolution succeeded
        - hostname: The queried hostname
        - ipv4_addresses: List of IPv4 addresses
        - ipv6_addresses: List of IPv6 addresses
        - canonical_name: Canonical hostname (CNAME)
        - error: Error message if resolution failed
        
    Example:
        >>> result = resolve_hostname("google.com")
        >>> print(f"IPv4: {result['ipv4_addresses']}")
    """
    try:
        # Get all address info
        addr_info = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        
        ipv4 = []
        ipv6 = []
        
        for info in addr_info:
            family = info[0]
            ip = info[4][0]
            
            if family == socket.AF_INET and ip not in ipv4:
                ipv4.append(ip)
            elif family == socket.AF_INET6 and ip not in ipv6:
                ipv6.append(ip)
        
        # Get canonical name
        try:
            canonical = socket.getfqdn(hostname)
        except Exception:
            canonical = hostname
        
        return {
            "success": True,
            "hostname": hostname,
            "ipv4_addresses": ipv4,
            "ipv6_addresses": ipv6,
            "canonical_name": canonical,
        }
        
    except socket.gaierror as e:
        return {
            "success": False,
            "hostname": hostname,
            "error": f"DNS resolution failed: {e}",
        }
    except Exception as e:
        return {
            "success": False,
            "hostname": hostname,
            "error": f"Resolution error: {str(e)}",
        }
