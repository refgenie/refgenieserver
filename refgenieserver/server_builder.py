import sys
import logging

from subprocess import run
from refgenconf import RefGenConf
from refgenconf.exceptions import GenomeConfigFormatError, ConfigNotCompliantError
from ubiquerg import checksum, size, is_command_callable

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
    if float(rgc[CFG_VERSION_KEY]) < float(REQ_CFG_VERSION):
        raise ConfigNotCompliantError("You need to update the genome config to v{} in order to use the archiver. "
                                      "The required version can be generated with refgenie >= {}".
                                      format(REQ_CFG_VERSION, REFGENIE_BY_CFG[REQ_CFG_VERSION]))
    try:
        server_rgc_path = os.path.join(rgc[CFG_ARCHIVE_KEY], os.path.basename(cfg_path))
    except KeyError:
        raise GenomeConfigFormatError("The config '{}' is missing a '{}' entry. Can't determine the desired archive.".
                                      format(cfg_path, CFG_ARCHIVE_KEY))
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
    rgc_server = RefGenConf(server_rgc_path) if os.path.exists(server_rgc_path) else rgc
    for genome in genomes:
        genome_dir = os.path.join(rgc[CFG_FOLDER_KEY], genome)
        target_dir = os.path.join(rgc[CFG_ARCHIVE_KEY], genome)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        genome_desc = rgc[CFG_GENOMES_KEY][genome].setdefault(CFG_GENOME_DESC_KEY, DESC_PLACEHOLDER)
        genome_checksum = rgc[CFG_GENOMES_KEY][genome].setdefault(CFG_CHECKSUM_KEY, CHECKSUM_PLACEHOLDER)
        genome_attrs = {CFG_GENOME_DESC_KEY: genome_desc,
                        CFG_CHECKSUM_KEY: genome_checksum}
        rgc_server.update_genomes(genome, genome_attrs)
        _LOGGER.debug("updating '{}' genome attributes...".format(genome))
        assets = asset or rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY].keys()
        if not assets:
            _LOGGER.error("No assets found")
            exit(1)
        else:
            _LOGGER.debug("Assets to be processed: {}".format(str(assets)))
        for asset_name in assets:
            asset_desc = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset_name].setdefault(CFG_ASSET_DESC_KEY,
                                                                                             DESC_PLACEHOLDER)
            asset_attrs = {CFG_ASSET_DESC_KEY: asset_desc}
            _LOGGER.debug("updating '{}/{}' asset attributes...".format(genome, asset_name))
            rgc_server.update_assets(genome, asset_name, asset_attrs)
            tags = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset_name][CFG_ASSET_TAGS_KEY].keys()
            for tag_name in tags:
                if not rgc.is_asset_complete(genome, asset_name, tag_name):
                    _LOGGER.info("'{}/{}:{}' is incomplete, skipping".format(genome, asset_name, tag_name))
                    rgc_server.remove_assets(genome, asset_name, tag_name)
                    continue
                file_name = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset_name][CFG_ASSET_TAGS_KEY][tag_name][CFG_ASSET_PATH_KEY]
                target_file = os.path.join(target_dir, "{}__{}".format(asset_name, tag_name) + ".tgz")
                input_file = os.path.join(genome_dir, file_name, tag_name)
                # these attributes have to be read from the original RefGenConf in case the archiver just increments
                # an existing server RefGenConf
                parents = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset_name][CFG_ASSET_TAGS_KEY][tag_name].\
                    setdefault(CFG_ASSET_PARENTS_KEY, [])
                children = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset_name][CFG_ASSET_TAGS_KEY][tag_name].\
                    setdefault(CFG_ASSET_CHILDREN_KEY, [])
                seek_keys = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset_name][CFG_ASSET_TAGS_KEY][tag_name].\
                    setdefault(CFG_SEEK_KEYS_KEY, {})
                if not os.path.exists(target_file) or force:
                    _LOGGER.info("creating asset '{}' from '{}'".format(target_file, input_file))
                    try:
                        _check_tgz(input_file, target_file, asset_name)
                    except OSError as e:
                        _LOGGER.warning(e)
                        continue
                    else:
                        _LOGGER.info("updating '{}/{}:{}' tag attributes...".format(genome, asset_name, tag_name))
                        tag_attrs = {CFG_ASSET_PATH_KEY: file_name,
                                     CFG_SEEK_KEYS_KEY: seek_keys,
                                     CFG_ARCHIVE_CHECKSUM_KEY: checksum(target_file),
                                     CFG_ARCHIVE_SIZE_KEY: size(target_file),
                                     CFG_ASSET_SIZE_KEY: size(input_file),
                                     CFG_ASSET_PARENTS_KEY: parents,
                                     CFG_ASSET_CHILDREN_KEY: children}
                        _LOGGER.debug("attr dict: {}".format(tag_attrs))
                        rgc_server.update_tags(genome, asset_name, tag_name, tag_attrs)
                        rgc_server.write(server_rgc_path)
                else:
                    _LOGGER.debug("'{}' exists".format(target_file))
    _LOGGER.info("builder finished; server config file saved to: '{}'".format(rgc_server.write(server_rgc_path)))


def _check_tgz(path, output, asset_name):
    """
    Check if file exists and tar it.
    If gzipping is requested, the availability of pigz software is checked and used.

    :param str path: path to the file to be tarred
    :param str output: path to the result file
    :param str asset_name: name of the asset
    :raise OSError: if the file/directory meant to be archived does not exist
    """
    # since the genome directory structure changed (added tag layer) in refgenie >= 0.7.0 we need to perform some
    # extra file manipulation before archiving to make the produced archive compatible with new and old versions
    # of refgenie CLI. The difference is that refgenie < 0.7.0 requires the asset to be archived with the asset-named
    # enclosing dir, but with no tag-named directory as this concept did not exist back then.
    if os.path.exists(path):
        cmd = "cd {p}; mkdir {an}; mv * {an}; "  # move the asset files to asset-named dir
        cmd += "tar -cvf - {an} | pigz > {o}; " if is_command_callable("pigz") else "tar -cvzf {o} {an}; "  # tar gzip
        cmd += "mv {an}/* .; rm -r {an}"  # move the files back to the tag-named dir and remove asset-named dir
        run(cmd.format(p=path, o=output, an=asset_name), shell=True)
    else:
        raise OSError("entity '{}' does not exist".format(path))
