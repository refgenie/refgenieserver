V = 0.1
SERVER_CFG_NAME = "refgenieserver_config.yaml"
import os
import sys
import yaml
import argparse
from refgenconf import (
    CFG_GENOMES_KEY,
    CFG_SERVER_KEY,
    CFG_FOLDER_KEY,
    CFG_ARCHIVE_KEY,
    CFG_ASSET_PATH_KEY,
)


class _VersionInHelpParser(argparse.ArgumentParser):
    def format_help(self):
        """ Add version information to help text. """
        return (
            "version: {}\n".format(V) + super(_VersionInHelpParser, self).format_help()
        )


def build_dir2yaml_parser():
    """
    Building argument parser

    :return argparse.ArgumentParser
    """
    banner = (
        "%(prog)s builds a refgenieserver config template for the directory structure."
        " Keep in mind that the produced config will require some adjustments."
    )
    additional_description = "\nhttps://github.com/databio/refgenieserver"

    parser = _VersionInHelpParser(description=banner, epilog=additional_description)

    parser.add_argument(
        "-V", "--version", action="version", version="%(prog)s {v}".format(v=V)
    )
    parser.add_argument(
        "-p",
        "--path",
        dest="path",
        help="A path to the directory that the YAML should be build for. If not provided, current working directory "
        "will be used ({})".format(os.getcwd()),
        default=None,
    )
    return parser


def dir_as_dict(path):
    """
    creates a dict out of a directory
    inspired by: https://gist.github.com/blaketmiller/ee85ec1b5ddf038aa923

    :param str path: path to dir
    :return:
    """
    directory = {}
    for dirname, dirnames, filenames in os.walk(path):
        dn = os.path.basename(dirname)
        directory[dn] = {}
        if dirnames:
            for d in dirnames:
                directory[dn].update(dir_as_dict(os.path.join(path, d)))
        else:
            directory[dn][CFG_ASSET_PATH_KEY] = dn
        return directory


def main():
    parser = build_dir2yaml_parser()
    args = parser.parse_args()
    p = os.path.abspath(args.path) if args.path is not None else os.getcwd()
    server_path = os.path.join(p, SERVER_CFG_NAME)
    try:
        with open(server_path, "w") as f:
            try:
                rgc = {
                    CFG_FOLDER_KEY: None,
                    CFG_SERVER_KEY: "http://www.refgenomes.databio.org",
                    CFG_ARCHIVE_KEY: None,
                    CFG_GENOMES_KEY: None,
                }
                rgc[CFG_GENOMES_KEY] = dir_as_dict(p)[os.path.basename(p)]
                yaml.dump(rgc, f)
                print("Server config written to: {}".format(server_path))
            except Exception as e:
                print("Encountered an error: '{}: {}'".format(e.__class__.__name__, e))
    except Exception as e:
        print("Encountered an error: '{}: {}'".format(e.__class__.__name__, e))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("Program canceled by user")
        sys.exit(1)
