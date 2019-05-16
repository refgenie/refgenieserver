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
            help="A path to the refgenie config file (YAML)",
            default=None)
        self.add_argument(
            "-p", "--port",
            dest="port",
            type=int,
            help="The port the webserver should be run on.", default=DEFAULT_PORT)


class BuilderParser(argparse.ArgumentParser):
    """ CLI parser tailored for this project """

    def __init__(self):

        super(BuilderParser, self).__init__(
            description="%(prog)s - builds a file tree for refgenie_server",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        self.add_argument(
            "-c", "--config",
            dest="config",
            help="a path to the refgenie config file (YAML)",
            default=None)
        self.add_argument(
            "-g", "--genome",
            dest="genome",
            help="genomes to build the server for. If provided, rebuild for these will be forced",
            default=None,
            nargs="*")
        self.add_argument(
            "-f", "--force",
            action="store_true",
            dest="force",
            help="whether the server file tree should be rebuilt even if exists")

