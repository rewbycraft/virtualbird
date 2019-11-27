import virtualbird.bridge
import virtualbird.utils
from pyroute2.common import uifname
from pyroute2 import NetNS, IPDB, netns, NSPopen
from typing import List
import logging
import subprocess


class BirdInterface(virtualbird.utils.UpDownAble):
    name: str
    ns: str
    addresses: List[str]

    def __init__(self, name: str, ns: str) -> None:
        self.name = name
        self.ns = ns
        self.addresses = []

    def create(self) -> None:
        raise NotImplementedError()

    def up(self) -> None:
        logging.info("Bringing up %s...", self.name)
        self.create()
        with IPDB() as ip:
            with ip.interfaces[self.name] as i:
                logging.info("Setting namespace for interface %s to %s...", self.name, self.ns)
                i.net_ns_fd = self.ns
        with IPDB(nl=NetNS(self.ns)) as ip:
            with ip.interfaces[self.name] as i:
                for addr in self.addresses:
                    logging.info("Adding address %s to %s...", addr, self.name)
                    i.add_ip(addr)
                logging.info("Setting %s up...", self.name)
                i.up()

    def down(self) -> None:
        logging.info("Bringing down %s...", self.name)
        with IPDB(nl=NetNS(self.ns)) as ip:
            with ip.interfaces[self.name] as i:
                logging.info("Removing %s...", self.name)
                i.remove()

    def add_address(self, addr: str) -> None:
        self.addresses.append(addr)


class BirdBridgeInterface(BirdInterface):
    bridge: virtualbird.bridge.Bridge
    hostifname: str

    def __init__(self, name: str, ns: str, bridge: virtualbird.bridge.Bridge) -> None:
        super().__init__(name, ns)
        self.bridge = bridge
        self.hostifname = uifname()

    def create(self) -> None:
        with IPDB() as ip:
            wd0 = ip.watchdog(ifname=self.hostifname)
            logging.info("Creating veth pair %s <-> %s...", self.hostifname, self.name)
            ip.create(ifname=self.hostifname, kind='veth', peer=self.name).commit()
            wd0.wait()
            with ip.interfaces[self.bridge.ifname] as br:
                with ip.interfaces[self.hostifname] as intf:
                    logging.info("Setting host-veth %s up...", self.hostifname)
                    intf.up()
                    logging.info("Adding host-veth %s to bridge %s...", self.hostifname, self.bridge.ifname)
                    br.add_port(intf)


class Bird(virtualbird.utils.UpDownAble):
    interfaces: List[BirdInterface]
    name: str
    ns: str
    upcommands: List[str]
    downcommands: List[str]
    birdconfig: str
    birdnsp: NSPopen

    def __init__(self, name: str):
        logging.info("Creating bird %s..", name)
        self.name = name
        self.ns = "vb_{}".format(name)
        self.interfaces = []
        self.upcommands = []
        self.downcommands = []
        self.birdconfig = ""

    def run_command(self, cmd: List[str], shell: bool = False) -> int:
        logging.info("Running: %s", cmd)
        nsp = NSPopen(self.ns, cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=shell)
        try:
            out = nsp.communicate()
            if out:
                if out[0]:
                    outstr = out[0].decode('UTF-8')
                    lines = outstr.splitlines()
                    for line in lines:
                        logging.info("STDOUT: %s", line)
                if out[1]:
                    outstr = out[1].decode('UTF-8')
                    lines = outstr.splitlines()
                    for line in lines:
                        logging.info("STDERR: %s", line)
            nsp.wait()
            return nsp.returncode
        finally:
            nsp.release()

    def up(self):
        logging.info("Bringing up %s...", self.name)
        netns.create(self.ns)
        with IPDB(nl=NetNS(self.ns)) as ip:
            wd0 = ip.watchdog(ifname="lo")
            wd0.wait()
            with ip.interfaces["lo"] as lo:
                logging.info("Setting lo up...")
                lo.up()
                lo.add_ip("127.0.0.1/8")
                lo.add_ip("::1/128")
        for intf in self.interfaces:
            intf.up()
        logging.info("Running upcommands...")
        for cmd in self.upcommands:
            self.run_command(['bash', '-c', cmd])
        if self.birdconfig != "":
            logging.info("Starting bird...")
            with open("/tmp/{}.conf".format(self.ns), 'w') as file:
                file.write(self.birdconfig)
            if self.run_command(['bird', '-c', "/tmp/{}.conf".format(self.ns), '-p']) == 0:
                self.birdnsp = NSPopen(self.ns, ['bird', '-c', "/tmp/{}.conf".format(self.ns), '-f', '-s', "/tmp/{}.sock".format(self.ns), '-P', "/tmp/{}.pid".format(self.ns)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            else:
                logging.warning("Not starting bird with invalid config")
                self.birdconfig = ""
        logging.info("Brought %s up!", self.name)

    def down(self):
        logging.info("Bringing down %s...", self.name)
        if self.birdconfig != "":
            logging.info("Stopping bird...")
            try:
                if self.birdnsp.poll() == None:
                    self.birdnsp.communicate()
                    self.birdnsp.terminate()
                    self.birdnsp.wait()
                else:
                    logging.warning("Bird was already dead.")
                self.birdnsp.release()
            except BrokenPipeError:
                logging.warning("Bird was already dead.")
            except KeyboardInterrupt:
                logging.warning("Bird was already dead.")
        for cmd in self.downcommands:
            self.run_command(['bash', '-c', cmd])
        for intf in self.interfaces:
            intf.down()
        netns.remove(self.ns)
        logging.info("Running downcommands...")
        logging.info("Brought %s down!", self.name)

    def add_bridge_interface(self, bridge: virtualbird.bridge.Bridge, addrs: List[str]):
        intf = BirdBridgeInterface("{}-eth{}".format(self.name, len(self.interfaces)), self.ns, bridge)
        for addr in addrs:
            intf.add_address(addr)
        self.interfaces.append(intf)

    def add_upcommand(self, cmd: str):
        self.upcommands.append(cmd)

    def add_downcommand(self, cmd: str):
        self.downcommands.append(cmd)

    def set_birdconfig(self, conf: str):
        self.birdconfig = conf
