import os
import sys
import logging

from subprocess import run
from refgenconf import RefGenConf
from ubiquerg import checksum, size

from .const import *


def archive(rgc, genome, asset, force, cfg_path):
    """
    Takes the RefGenConf object and builds individual tar archives
    that can be then served with 'refgenieserver serve'. Additionally determines their md5 checksums, file sizes and
    updates the original refgenie config with these data. If the --asset and/or --genome options  are used (specific
    build is requested) the archiver will check for the existence of config file saved in the path provided in
    `genome_server` in the original config and update it so that no archive metadata is lost

    :param RefGenConf rgc: configuration object with the data to build the servable archives for
    :param str genome: genome to build archives for
    :param str asset: asset to build archives for
    :param bool force: whether to force the build of archive, regardless of its existence
    :param str cfg_path: config file path
    """
    global _LOGGER
    _LOGGER = logging.getLogger(PKG_NAME)
    server_rgc_path = os.path.join(rgc[CFG_ARCHIVE_KEY], os.path.basename(cfg_path))
    if asset and not genome:
        _LOGGER.error("You need to specify a genome (--genome) to request a specific asset build (--asset)")
        sys.exit(1)
    if force:
        _LOGGER.info("build forced; file existence will be ignored")
    if genome:
        _LOGGER.info("specific build requested for a genome: {}".format(genome))
        genomes = genome
        if asset:
            _LOGGER.info("specific build requested for assets: {}".format(asset))
        if os.path.exists(server_rgc_path):
            _LOGGER.debug("'{}' file was found and will be updated".format(server_rgc_path))
    else:
        genomes = rgc.genomes_list()
    if not genomes:
        _LOGGER.error("No genomes found")
        exit(1)
    else:
        _LOGGER.debug("Genomes to be processed: {}".format(str(genomes)))
    for genome in genomes:
        genome_dir = os.path.join(rgc[CFG_FOLDER_KEY], genome)
        target_dir = os.path.join(rgc[CFG_ARCHIVE_KEY], genome)
        genome_tarball = target_dir + TAR["ext"]
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        changed = False
        genome_desc = rgc[CFG_GENOMES_KEY][genome].setdefault(CFG_GENOME_DESC_KEY, DESC_PLACEHOLDER)
        genome_checksum = rgc[CFG_GENOMES_KEY][genome].setdefault(CFG_CHECKSUM_KEY, CHECKSUM_PLACEHOLDER)
        assets = asset or rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY].keys()
        if not assets:
            _LOGGER.error("No assets found")
            exit(1)
        else:
            _LOGGER.debug("Assets to be processed: {}".format(str(assets)))
        for asset_name in assets:
            tags = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset_name].keys()
            # the asset level keys include the asset tags and the CFG_ASSET_DEFAULT_TAG_KEY
            tags.remove(CFG_ASSET_DEFAULT_TAG_KEY)
            for tag_name in tags:
                file_name = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset_name][tag_name][CFG_ASSET_PATH_KEY]
                asset_desc = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset_name][tag_name].\
                    setdefault(CFG_ASSET_DESC_KEY, DESC_PLACEHOLDER)
                target_file = os.path.join(target_dir, "{}__{}".format(asset_name, tag_name) + TGZ["ext"])
                input_file = os.path.join(genome_dir, file_name, tag_name)
                if not os.path.exists(target_file) or force:
                    changed = True
                    _LOGGER.info("creating asset '{}' from '{}'".format(target_file, input_file))
                    try:
                        _check_tar(input_file, target_file, TGZ["flags"])
                    except OSError as e:
                        _LOGGER.warning(e)
                        continue
                else:
                    _LOGGER.debug("'{}' exists".format(target_file))
                _LOGGER.info("updating '{}/{}:{}' attributes...".format(genome, asset_name, tag_name))
                genome_attrs = {CFG_GENOME_DESC_KEY: genome_desc,
                                CFG_CHECKSUM_KEY: genome_checksum}
                asset_attrs = {CFG_ASSET_PATH_KEY: file_name,
                               CFG_ASSET_DESC_KEY: asset_desc,
                               CFG_ARCHIVE_CHECKSUM_KEY: checksum(target_file),
                               CFG_ARCHIVE_SIZE_KEY: size(target_file),
                               CFG_ASSET_SIZE_KEY: size(input_file)}
                rgc_server = RefGenConf(server_rgc_path) if os.path.exists(server_rgc_path) else rgc
                rgc_server.update_genomes(genome, genome_attrs)
                rgc_server.update_assets(genome, asset_name, tag_name, asset_attrs)
                rgc_server.write(server_rgc_path)
        if changed or not os.path.exists(genome_tarball):
            _LOGGER.info("creating genome tarball '{}' from '{}'".format(genome_tarball, genome_dir))
            try:
                _check_tar(target_dir, genome_tarball, TAR["flags"])
            except OSError as e:
                _LOGGER.warning(e)
                continue
    _LOGGER.info("builder finished; server config file saved to: '{}'".format(rgc_server.write(server_rgc_path)))


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