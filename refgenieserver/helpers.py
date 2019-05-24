import argparse
from const import *
from _version import __version__ as v
from yacman import get_first_env_var


class _VersionInHelpParser(argparse.ArgumentParser):
    def format_help(self):
        """ Add version information to help text. """
        return "version: {}\n".format(v) + super(_VersionInHelpParser, self).format_help()


def build_parser():
    """
    Building argument parser

    :return argparse.ArgumentParser
    """
    env_var_val = get_first_env_var(CFG_ENV_VARS)[1] if get_first_env_var(CFG_ENV_VARS) is not None else "not set"
    banner = "%(prog)s - refgenie web server utilities"
    additional_description = "For subcommand-specific options, type: '%(prog)s <subcommand> -h'"
    additional_description += "\nhttps://github.com/databio/refgenieserver"

    parser = _VersionInHelpParser(
        description=banner,
        epilog=additional_description)

    parser.add_argument(
        "-V", "--version",
        action="version",
        version="%(prog)s {v}".format(v=v))
    parser.add_argument(
        "-c", "--config",
        dest="config",
        help="A path to the refgenie config file (YAML). If not provided, the first available environment variable "
             "among: \'{}\' will be used if set. Currently {}".format(", ".join(CFG_ENV_VARS), env_var_val),
        default=None)
    parser.add_argument(
        "-d", "--dbg",
        action="store_true",
        dest="debug",
        help="Set logger verbosity to debug")

    msg_by_cmd = {
        "serve": "run the server",
        "archive": "prepare servable archives"}

    subparsers = parser.add_subparsers(dest="command")

    def add_subparser(cmd):
        message = msg_by_cmd[cmd]
        return subparsers.add_parser(cmd, description=message, help=message)

    # Run and rerun command
    serve_subparser = add_subparser("serve")
    archive_subparser = add_subparser("archive")
    serve_subparser.add_argument(
        "-p", "--port",
        dest="port",
        type=int,
        help="The port the webserver should be run on.", default=DEFAULT_PORT)
    archive_subparser.add_argument(
        "-f", "--force",
        action="store_true",
        dest="force",
        help="whether the server file tree should be rebuilt even if exists")
    return parser
