import argparse
from const import DEFAULT_PORT


class Parser(argparse.ArgumentParser):
    """ CLI parser tailored for this project """

    def __init__(self):

        super(Parser, self).__init__(
            description="%(prog)s - run a refgenie web server",
            epilog="See docs at: http://refgenie.databio.org/",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        self.add_argument(
            "-c", "--config",
            dest="config",
            help="Refgenie config file (YAML)")
        self.add_argument(
            "-p", "--port",
            dest="port",
            type=int,
            help="The port the webserver should be run on.", default=DEFAULT_PORT)
