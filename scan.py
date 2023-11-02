import nmap

def scan_network():
    print("Scanning network for active IP addresses...")

    nm = nmap.PortScanner()
    nm.scan(hosts='192.168.1.0/24', arguments='-sn')

    for host in nm.all_hosts():
        print(f"Found active IP: {host}")

    print("Scan complete.")

if __name__ == "__main__":
    scan_network()
