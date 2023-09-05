import json
import os
import subprocess

import kthread
import requests
from pfehler import pfehler
import platform

import kthread_sleep
from dynuipv4update import ipconfig, update_dynamic_dns

iswindows = "win" in platform.platform().lower()
fi = os.path.normpath(os.sep.join(os.path.abspath(__file__).split(os.sep)[0:-1]))
os.chdir(fi)
winexe = os.path.normpath(os.path.join(fi, "rsocx.exe")).replace("/", "\\")
linuxexe = os.path.normpath(os.path.join(fi, "rsocx")).replace("\\", "/")


def create_config_file(
    network_config_for_linux,
    linux_username,
    su_password,
    execute_linux_network_patches=True,
    portstart=8000,
    portstart_small=1080,
    nameserver="8.8.8.8",
):
    alllines = []
    sysctldone = False
    startdata = []
    nameserverdone = False
    invokeservers = []
    for key, item in network_config_for_linux.items():
        mynamespace = item["mynamespace"]
        virtual1 = item["virtual1"]
        virtual2 = item["virtual2"]
        ip0 = item["ip0"]
        ip1 = item["ip1"]
        ip2 = item["ip2"]
        ip3 = item["ip3"]
        interface = item["interface"]

        alllines.append(rf"sudo ip netns add {mynamespace}")
        alllines.append(rf"sudo ip link add {virtual1} type veth peer name {virtual2}")
        alllines.append(rf"sudo ip link set {virtual2} netns {mynamespace}")
        alllines.append(rf"sudo ip link set dev {virtual1} up")
        alllines.append(
            rf"sudo ip netns exec {mynamespace} ip link set dev {virtual2} up"
        )
        alllines.append(rf"sudo ip addr add {ip1} dev {virtual1}")
        alllines.append(rf"sudo ip route add {ip2} dev {virtual1}")
        alllines.append(
            rf"sudo iptables -t nat -A POSTROUTING -o {interface} -j MASQUERADE"
        )
        if not sysctldone:
            alllines.append(rf"sudo sysctl net.ipv4.ip_forward=1")
            sysctldone = True
        alllines.append(
            rf"sudo ip netns exec {mynamespace} ip addr add {ip3} dev {virtual2}"
        )
        alllines.append(
            rf"sudo ip netns exec {mynamespace} ip route add default via {ip0}"
        )
        if not nameserverdone and nameserver:
            alllines.append(
                f'echo "nameserver {nameserver}" | sudo tee /etc/resolv.conf'
            )
            nameserverdone = True
        startdata.append(
            [
                mynamespace,
                portstart,
            ]
        )

        invokeserver = [
            winexe,
            "-t",
            f"0.0.0.0:{portstart}",
            "-s",
            f"0.0.0.0:{portstart_small}",
        ]
        invokeservers.append(invokeserver)
        portstart = portstart + 1
        portstart_small = portstart_small + 1
    if not iswindows:
        if execute_linux_network_patches:
            subprocess.run(
                "su",
                input=(
                    su_password.encode()
                    if not isinstance(su_password, bytes)
                    else su_password
                )
                + (
                    b'\n\necho "' + linux_username.encode()
                    if not isinstance(linux_username, bytes)
                    else linux_username
                )
                + b' ALL=(ALL) NOPASSWD: ALL" | tee /etc/sudoers\n\n',
                shell=True,
            )
            for l in alllines:
                print(l)
                subprocess.run(
                    l,
                    shell=True,
                )

    return startdata, invokeservers


def get_linux_network_config(
    interfaces=("enx344b50000000", "eth0"),
    networkprefix="nspace",
    virtualnetworkprefix="veth",
    ipprefix="192.168",
):
    networkprefixcounter = 0
    virtualnetworkprefixcounter = 0
    ipcounter = 1
    allinterfaces = {}
    for index, interface in enumerate(interfaces):
        network_config_for_linux = {
            "mynamespace": f"{networkprefix}{networkprefixcounter}",
            "virtual1": "veth0",
            "virtual2": "veth1",
            "ip0": f"{ipprefix}.{ipcounter}.1",
            "ip1": f"{ipprefix}.{ipcounter}.1/24",
            "ip2": f"{ipprefix}.{ipcounter}.0/24",
            "ip3": f"{ipprefix}.{ipcounter}.2/24",
            "interface": interface,
        }

        ipcounter += 1
        network_config_for_linux[
            "virtual1"
        ] = f"{virtualnetworkprefix}{virtualnetworkprefixcounter}"
        virtualnetworkprefixcounter += 1
        network_config_for_linux[
            "virtual2"
        ] = f"{virtualnetworkprefix}{virtualnetworkprefixcounter}"
        virtualnetworkprefixcounter += 1
        networkprefixcounter += 1
        allinterfaces[index] = network_config_for_linux.copy()
    return allinterfaces


def start_subproc(ip, port, adapter_name, su_password):
    print(f"ip netns exec {adapter_name} {linuxexe} -r {ip}:{port}".encode("utf-8"))
    try:
        while True:
            try:
                _ = subprocess.run(
                    "su",
                    shell=True,
                    input=(
                        su_password.encode("utf-8")
                        if not isinstance(su_password, bytes)
                        else su_password
                    )
                    + b"\n\n"
                    + f"ip netns exec {adapter_name} {linuxexe} -r {ip}:{port}".encode(
                        "utf-8"
                    ),
                )
                kthread_sleep.sleep(5)
                continue
            except Exception as e:
                pfehler()
                kthread_sleep.sleep(5)
                continue

    except KeyboardInterrupt:
        pass


def start_subproc_win(invokeserver):
    try:
        while True:
            try:
                _ = subprocess.run(invokeserver, shell=True)
                kthread_sleep.sleep(5)
                continue
            except Exception as e:
                pfehler()
                kthread_sleep.sleep(5)
                continue
    except KeyboardInterrupt:
        pass


def start_reverse_client_linux_win(
    supassword,
    ip,
    port,
    adapter_name,
    allthreads,
    invokeserver,
):
    if not iswindows:
        allthreads.append(
            kthread.KThread(
                target=start_subproc,
                kwargs={
                    "ip": ip,
                    "port": port,
                    "adapter_name": adapter_name,
                    "su_password": supassword,
                },
            )
        )

    else:
        allthreads.append(
            kthread.KThread(
                target=start_subproc_win,
                kwargs={"invokeserver": invokeserver},
            )
        )

    allthreads[-1].daemon = True
    allthreads[-1].start()


def update_ip(apikey, second_level_domain, top_level_domain, dyn_password, frequency):
    if iswindows:
        update_dynamic_dns(
            apikey=apikey,
            subdomain=second_level_domain,
            domain=top_level_domain,
            password=dyn_password,
            as_thread=True,
            frequency=frequency,
            print_update=True,
        )

    while not ipconfig.allipscans:
        kthread_sleep.sleep(0.1)
    print(ipconfig.allipscans[f"{second_level_domain}.{top_level_domain}"])


def configure_ethernet_and_start_proxies(
    apikey: str,  # get it from https://www.dynu.com/en-US/ControlPanel/APICredentials
    dyn_password: str,  # get it from https://www.dynu.com/en-US/ControlPanel/APICredentials
    subdomain: str,  # get it from https://www.dynu.com/en-US/ControlPanel/DDNS
    domain: str,  # get it from https://www.dynu.com/en-US/ControlPanel/DDNS
    interfaces: list
    | tuple,  # use "ip route" (linux) to find out which interfaces you want to use
    linux_username: str,  # the username of the linux user you want to use
    su_password: str,  # the su password (linux)
    sleep_ip_update: int = 30,  # frequency to update the ip address
    execute_linux_network_patches: bool = True,  # if True, it will execute the commands to create the virtual interfaces
    nameserver: str = "8.8.8.8",  # the nameserver you want to use
    networkprefix: str = "nspace",  # the prefix for the network namespace
    virtualnetworkprefix: str = "veth",  # the prefix for the virtual network interfaces
    ipprefix: str = "192.168",  # the prefix for the ip addresses
    port_start_reverse: int = 8000,  # the port where the reverse proxy will start
    port_start_proxy: int = 1080,  # the port where the proxy will start
):
    """
    Configure Ethernet and Start Proxies

    This function configures network interfaces, sets up network namespaces and virtual interfaces,
    and starts reverse proxies and DNS updates based on the provided parameters.
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
    """
    if iswindows:
        update_ip(apikey, subdomain, domain, dyn_password, sleep_ip_update)
    forinterfaces, invokeservers = create_config_file(
        network_config_for_linux=get_linux_network_config(
            interfaces=interfaces,
            networkprefix=networkprefix,
            virtualnetworkprefix=virtualnetworkprefix,
            ipprefix=ipprefix,
        ),
        linux_username=linux_username,
        execute_linux_network_patches=execute_linux_network_patches,
        su_password=su_password,
        nameserver=nameserver,
        portstart=port_start_reverse,
        portstart_small=port_start_proxy,
    )
    allthreads = []
    for mynamespace__portstart, i in zip(forinterfaces, invokeservers):
        try:
            myip = ipconfig.allipscans[f"{subdomain}.{domain}"][-1][-1]
        except Exception:
            with requests.get(
                "https://api.dynu.com/v2/dns",
                headers={"accept": "application/json", "API-Key": apikey},
            ) as rea:
                (rea) = rea.content
            myip = [
                (x[1][0]["unicodeName"], x[1][0]["ipv4Address"])
                for x in json.loads(rea).items()
                if x[0] == "domains"
            ][0][-1]
        mynamespace, portstart = mynamespace__portstart
        start_reverse_client_linux_win(
            supassword=su_password,
            ip=myip,
            port=portstart,
            adapter_name=mynamespace,
            allthreads=allthreads,
            invokeserver=i,
        )
