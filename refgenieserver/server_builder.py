import os
import sys

from subprocess import run
from hashlib import md5
import logging
from refgenconf import RefGenConf
from ubiquerg import checksum

from .const import *


def archive(rgc, args):
    """
    Takes the RefGenConf object and builds the individual tar archives
    that can be then served with 'refgenieserver serve'. Additionally determines their md5 checksums, file sizes and
    updates the original refgenie config with these data.

    :param RefGenConf rgc: configuration object with the data to build the servable archives for
    :param argparse.Namespace args: arguments from the refgenieserver CLI
    """
    global _LOGGER
    _LOGGER = logging.getLogger(PKG_NAME)
    _LOGGER.debug("Args: {}".format(args))
    if args.force:
        _LOGGER.info("build forced; file existence will be ignored")
    server_rgc_path = os.path.join(rgc[CFG_ARCHIVE_KEY], os.path.basename(args.config))
    genomes = rgc.genomes_list()
    for genome in genomes:
        genome_dir = os.path.join(rgc[CFG_FOLDER_KEY], genome)
        target_dir = os.path.join(rgc[CFG_ARCHIVE_KEY], genome)
        genome_tarball = target_dir + TAR["ext"]
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        changed = False
        for asset_name in rgc.genomes[genome].keys():
            file_name = rgc.genomes[genome][asset_name][CFG_ASSET_PATH_KEY]
            target_file = os.path.join(target_dir, asset_name + TGZ["ext"])
            input_file = os.path.join(genome_dir, file_name)
            if not os.path.exists(target_file) or args.force:
                changed = True
                _LOGGER.info("creating asset '{}' from '{}'".format(target_file, input_file))
                try:
                    _check_tar(input_file, target_file, TGZ["flags"])
                except OSError as e:
                    _LOGGER.warning(e)
                    continue
            else:
                _LOGGER.info("'{}' exists".format(target_file))
            _LOGGER.info("updating '{}: {}' attributes...".format(genome, asset_name))
            asset_attrs = {CFG_CHECKSUM_KEY: checksum(target_file),
                           CFG_ARCHIVE_SIZE_KEY: _size(target_file),
                           CFG_ASSET_SIZE_KEY: _size(input_file)}
            rgc.update_genomes(genome, asset_name, asset_attrs)
            rgc.write(server_rgc_path)
        if changed or not os.path.exists(genome_tarball):
            _LOGGER.info("creating genome tarball '{}' from '{}'".format(genome_tarball, genome_dir))
            try:
                _check_tar(target_dir, genome_tarball, TAR["flags"])
            except OSError as e:
                _LOGGER.warning(e)
                continue
    _LOGGER.info("builder finished; server config file saved to: '{}'".format(rgc.write(server_rgc_path)))


def _check_tar(path, output, flags):
    """
    Checks if file exists and tars it

    :param str path: path to the file to be tarred
    :param str output: path to the result file
    :param str flags: tar command flags to use
    :return:
    """
    # TODO: maybe use the tarfile package (it is much slower than shell), some example code below:
    # import tarfile
    # with tarfile.open(output, "w:gz") as tar:
    #     tar.add(path, arcname=os.path.basename(path))
    if os.path.exists(path):
        enclosing_dir = os.path.dirname(path)
        entity_name = os.path.basename(path)
        # use -C (cd to the specified dir before taring) option not to include the directory structure in the archive
        run("tar -C {} {} {} {}".format(enclosing_dir, flags, output, entity_name), shell=True)
    else:
        raise OSError("entity '{}' does not exist".format(path))


def _size(path):
    """
    Gets the size the file or directory in the provided path

    :param str path: path to the file to check size of
    :return int: file size
    """
    global _LOGGER
    if os.path.isfile(path):
        s = _size_str(os.path.getsize(path))
    elif os.path.isdir(path):
        s = 0
        symlinks = []
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    s += os.path.getsize(fp)
                else:
                    s += os.lstat(fp).st_size
                    symlinks.append(fp)
        if len(symlinks) > 0:
            _LOGGER.info("{} symlinks were found: '{}'".format(len(symlinks), "\n".join(symlinks)))
    else:
        _LOGGER.warning("size could not be determined for: '{}'".format(path))
        s = None
    return _size_str(s)


def _size_str(size):
    """
    Converts the numeric bytes to the size string

    :param int|float size: file size to convert
    :return str: file size string
    """
    if isinstance(size, (int, float)):
        for unit in FILE_SIZE_UNITS:
            if size < 1024:
                return "{}{}".format(round(size, 1), unit)
            size /= 1024
    return size
