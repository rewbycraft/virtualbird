from typing import Dict
from virtualbird import bridge, bird
import logging
import virtualbird.utils


class Environment(virtualbird.utils.UpDownAble):
    bridges: Dict[str, bridge.Bridge]
    birds: Dict[str, bird.Bird]

    def __init__(self) -> None:
        self.bridges = {}
        self.birds = {}

    def add_bridge(self, ifname: str) -> None:
        if ifname not in self.bridges:
            logging.info("Creating new bridge %s,..", ifname)
            self.bridges[ifname] = bridge.Bridge(ifname)

    def add_bird(self, name: str, config):
        if name not in self.birds:
            logging.info("Creating new bird %s...", name)
            self.birds[name] = bird.Bird(name)
            if "interfaces" in config:
                for intf in config["interfaces"]:
                    if "bridge" in intf:
                        self.birds[name].add_bridge_interface(self.bridges[intf["bridge"]], intf["addresses"])
            if "up" in config:
                for cmd in config["up"]:
                    self.birds[name].add_upcommand(cmd)
            if "down" in config:
                for cmd in config["down"]:
                    self.birds[name].add_downcommand(cmd)
            if "bird" in config:
                self.birds[name].set_birdconfig(config["bird"])

    def up(self):
        logging.info("Bringing environment up...")
        for n, br in self.bridges.items():
            br.up()
        for n, bi in self.birds.items():
            bi.up()
        logging.info("Brought environment up!")

    def down(self):
        logging.info("Bringing environment down...")
        for n, br in self.bridges.items():
            br.down()
        for n, bi in self.birds.items():
            bi.down()
        logging.info("Brought environment down!")


