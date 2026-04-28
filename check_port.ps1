$ProgressPreference = 'SilentlyContinue'
$tcp = New-Object Net.Sockets.TcpClient
try {
    $tcp.Connect('127.0.0.1', 6000)
    if ($tcp.Connected) {
        exit 0
    } else {
        exit 1
    }
} catch {
    exit 1
}
