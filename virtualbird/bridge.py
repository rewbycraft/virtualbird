from pyroute2 import IPDB
import virtualbird.utils
import logging


class Bridge(virtualbird.utils.UpDownAble):
    ifname: str

    def __init__(self, name: str) -> None:
        self.ifname = "vb_" + name

    def up(self) -> None:
        logging.info("Bringing %s up...", self.ifname)
        with IPDB() as ip:
            wd0 = ip.watchdog(ifname=self.ifname)
            ip.create(kind='bridge', ifname=self.ifname).commit()
            wd0.wait()
            ip.interfaces[self.ifname].up().commit()

    def down(self) -> None:
        logging.info("Bringing %s down...", self.ifname)
        with IPDB() as ip:
            ip.interfaces[self.ifname].remove().commit()
