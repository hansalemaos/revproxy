# Reverse Proxy

## Tested against Windows 10 / Python 3.10 / Anaconda and Ubuntu

## pip install revproxy

```python
configure_ethernet_and_start_proxies
This function configures network interfaces, sets up network namespaces and virtual interfaces,
and starts reverse proxies (using https://github.com/b23r0/rsocx) and DNS updates based on the provided parameters.
The function has to be executed with the same arguments on the server (Linux) and the client (Windows).
You must disable ipv6!


Parameters:
- apikey (str): API key for Dynu DNS service (https://www.dynu.com/en-US/ControlPanel/APICredentials).
- dyn_password (str): Password for Dynu DNS service (https://www.dynu.com/en-US/ControlPanel/APICredentials).
- subdomain (str): Subdomain to update DNS records for (https://www.dynu.com/en-US/ControlPanel/DDNS).
- domain (str): Top-level domain to update DNS records for (https://www.dynu.com/en-US/ControlPanel/DDNS).
- interfaces (list or tuple): List of network interfaces to use for configuration (use "ip route" on Linux to find interfaces).
- linux_username (str): The username of the Linux user to use for network configuration.
- su_password (str): The superuser (su) password for Linux.
- sleep_ip_update (int): Frequency in seconds to update the IP address.
- execute_linux_network_patches (bool): If True, execute commands to create virtual network interfaces on Linux.
- nameserver (str): The nameserver to use for DNS resolution.
- networkprefix (str): Prefix for network namespaces.
- virtualnetworkprefix (str): Prefix for virtual network interfaces.
- ipprefix (str): Prefix for IP addresses.
- port_start_reverse (int): Port where the reverse proxy will start.
- port_start_proxy (int): Port where the proxy will start.
```