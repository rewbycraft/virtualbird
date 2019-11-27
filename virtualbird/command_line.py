import logging
import virtualbird.environment
import time
import argparse
import yaml
import pprint

def main():
    logging.basicConfig(format='%(asctime)s %(levelname)s: %(message)s', level=logging.DEBUG)
    logging.info("Hello!")
    parser = argparse.ArgumentParser(description='Virtual networks with BIRD')
    parser.add_argument('config', type=str, help='environment configuration')
    args = parser.parse_args()

    with open(args.config, 'r') as stream:
        data = yaml.safe_load(stream)
        logging.info("Config:")
        logging.info(pprint.pformat(data, indent=4))
        env = virtualbird.environment.Environment()
        if "environment" in data:
            data_env = data["environment"]
            if "bridges" in data_env:
                for name in data_env["bridges"]:
                    env.add_bridge(name)
            if "birds" in data_env:
                for name, config in data_env["birds"].items():
                    env.add_bird(name, config)
        try:
            env.up()
            try:
                logging.info("Done! Idling... (Use ctrl-c to stop.)")
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                logging.info("Caught interrupt, stopping...")

        finally:
            env.down()


if __name__ == "__main__":
    main()
