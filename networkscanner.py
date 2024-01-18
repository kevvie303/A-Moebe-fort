import paramiko
import os
import nmap
import socket
import ipaddress
class NetworkScanner:
    def __init__(self):
        self.nm = nmap.PortScanner()
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def get_current_network_range(self):
        # Get the current IP address of the host
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Connecting to a public DNS server
        ip_address = s.getsockname()[0]
        s.close()

        # Calculate the network range
        host_ip = ipaddress.ip_address(ip_address)
        network = ipaddress.ip_network(f'{host_ip}/24', strict=False)
        return str(network)

    def get_hostname_via_ssh(self, ip_address):
        try:
            self.ssh.connect(ip_address, username=os.getenv("SSH_USERNAME"), password=os.getenv("SSH_PASSWORD"))
            stdin, stdout, stderr = self.ssh.exec_command('hostname')
            hostname = stdout.read().decode().strip()
            self.ssh.close()
            return hostname
        except Exception as e:
            print(f"Error retrieving hostname for {ip_address}: {e}")
            return None

    def scan_for_raspberrypi(self):
        range = self.get_current_network_range()
        self.nm.scan(hosts=range, arguments='-sP')
        pi_devices = []
        for host in self.nm.all_hosts():
            mac_address = self.nm[host]['addresses'].get('mac', None)
            if mac_address and (mac_address.startswith("B8:27:EB") or mac_address.startswith("DC:A6:32")):
                hostname = self.get_hostname_via_ssh(host)
                pi_devices.append((host, mac_address, hostname))
        return pi_devices
