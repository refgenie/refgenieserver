from __future__ import annotations

import logging
import sys
from glob import glob
from json import dump
from subprocess import run

from refgenconf import RefGenConf
from refgenconf.exceptions import (
    ConfigNotCompliantError,
    GenomeConfigFormatError,
    MissingConfigDataError,
    RefgenconfError,
)
from refgenconf.helpers import replace_str_in_obj, swap_names_in_tree
from ubiquerg import checksum, is_command_callable, parse_registry_path, size
from yacman import write_lock

from .const import *

global _LOGGER
_LOGGER = logging.getLogger(PKG_NAME)


def archive(
    rgc: RefGenConf,
    registry_paths: list[dict] | None,
    force: bool,
    remove: bool,
    cfg_path: str,
    genomes_desc: str | None,
) -> None:
    """Build tar archives for serving with 'refgenieserver serve'.

    Determines md5 checksums and file sizes and updates the original refgenie
    config with these data. If specific assets/genomes are requested, checks
    for the server config file and updates it to preserve archive metadata.

    Args:
        rgc: Configuration object with data to build servable archives for.
        registry_paths: Collection of mappings identifying assets to update.
        force: Whether to force the build regardless of existence.
        remove: Whether to remove specified genome/asset:tag from the archive.
        cfg_path: Config file path.
        genomes_desc: Path to CSV file with genome descriptions.
    """
    if float(rgc[CFG_VERSION_KEY]) < float(REQ_CFG_VERSION):
        raise ConfigNotCompliantError(
            f"You need to update the genome config to v{REQ_CFG_VERSION} in order to use the archiver. "
            f"The required version can be generated with refgenie >= {REFGENIE_BY_CFG[REQ_CFG_VERSION]}"
        )
    if CFG_ARCHIVE_CONFIG_KEY in rgc:
        srp = rgc[CFG_ARCHIVE_CONFIG_KEY]
        server_rgc_path = (
            srp
            if os.path.isabs(srp)
            else os.path.join(os.path.dirname(rgc.file_path), srp)
        )
    else:
        try:
            server_rgc_path = os.path.join(
                rgc[CFG_ARCHIVE_KEY], os.path.basename(cfg_path)
            )
        except KeyError:
            raise GenomeConfigFormatError(
                f"The config '{cfg_path}' is missing a {' or '.join([CFG_ARCHIVE_KEY, CFG_ARCHIVE_KEY_OLD])} entry. "
                f"Can't determine the desired archive."
            )
    if os.path.isfile(server_rgc_path) and not os.access(server_rgc_path, os.W_OK):
        raise OSError(
            "The determined archive config path is not writable: {}".format(
                server_rgc_path
            )
        )
    if force:
        _LOGGER.info("Build forced; file existence will be ignored")
    _LOGGER.debug("Registry_paths: {}".format(registry_paths))
    # original RefGenConf has been created in read-only mode,
    # make it RW compatible and point to new target path for server use or initialize a new object
    if os.path.exists(server_rgc_path):
        _LOGGER.debug(f"'{server_rgc_path}' file was found and will be updated")
        rgc_server = RefGenConf.from_yaml_file(server_rgc_path)
        if remove:
            if not registry_paths:
                _LOGGER.error(
                    "To remove archives you have to specify them. "
                    "Use 'asset_registry_path' argument."
                )
                exit(1)
            with write_lock(rgc_server) as r:
                _remove_archive(r, registry_paths, CFG_ARCHIVE_KEY)
                r.write()
            exit(0)
    else:
        if remove:
            _LOGGER.error(
                "You can't remove archives since the genome_archive path does not exist yet."
            )
            exit(1)
        _LOGGER.debug(f"'{server_rgc_path}' file was not found and will be created")
        rgc_server = RefGenConf.from_yaml_file(rgc.file_path)
        rgc_server.write_copy(server_rgc_path)
        rgc_server.filepath = os.path.abspath(server_rgc_path)
        rgc_server.locker.set_file_path(os.path.abspath(server_rgc_path))
    if registry_paths:
        genomes = _get_paths_element(registry_paths, "namespace")
        asset_list = _get_paths_element(registry_paths, "item")
        tag_list = _get_paths_element(registry_paths, "tag")
    else:
        genomes = rgc.genomes_list()
        asset_list, tag_list = None, None
    if not genomes:
        _LOGGER.error("No genomes found")
        exit(1)
    else:
        _LOGGER.debug(f"Genomes to be processed: {str(genomes)}")
    genomes = [rgc.get_genome_alias_digest(g) for g in genomes]
    if genomes_desc is not None:
        if os.path.exists(genomes_desc):
            import csv

            _LOGGER.info(f"Found a genomes descriptions CSV file: {genomes_desc}")
            with open(genomes_desc, mode="r") as infile:
                reader = csv.reader(infile)
                descs = {rows[0]: rows[1] for rows in reader}
        else:
            _LOGGER.error(
                f"Genomes descriptions CSV file does not exist: {genomes_desc}"
            )
            sys.exit(1)
    counter = 0
    for genome in genomes:
        genome_dir = os.path.join(rgc.data_dir, genome)
        target_dir = os.path.join(rgc[CFG_ARCHIVE_KEY], genome)
        alias_target_dir = os.path.join(
            rgc[CFG_ARCHIVE_KEY], rgc.get_genome_alias(digest=genome, fallback=True)
        )
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
            # create legacy directory for archive
            # TODO: remove in the future
            os.makedirs(alias_target_dir, exist_ok=True)
        genome_desc = (
            rgc[CFG_GENOMES_KEY][genome].setdefault(
                CFG_GENOME_DESC_KEY, DESC_PLACEHOLDER
            )
            if genomes_desc is None or genome not in descs
            else descs[genome]
        )
        genome_aliases = rgc[CFG_GENOMES_KEY][genome].setdefault(CFG_ALIASES_KEY, [])
        genome_attrs = {
            CFG_GENOME_DESC_KEY: genome_desc,
            CFG_ALIASES_KEY: genome_aliases,
        }
        with write_lock(rgc_server) as r:
            r[CFG_GENOMES_KEY].setdefault(genome, {})
            r[CFG_GENOMES_KEY][genome].update(genome_attrs)
            r.write()
        _LOGGER.debug(f"Updating '{genome}' genome attributes...")
        asset = asset_list[counter] if asset_list is not None else None
        assets = asset or list(rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY].keys())
        if not assets:
            _LOGGER.error("No assets found")
            continue
        else:
            _LOGGER.debug(f"Assets to be processed: {str(assets)}")
        for asset_name in assets if isinstance(assets, list) else [assets]:
            asset_desc = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][
                asset_name
            ].setdefault(CFG_ASSET_DESC_KEY, DESC_PLACEHOLDER)
            default_tag = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][
                asset_name
            ].setdefault(CFG_ASSET_DEFAULT_TAG_KEY, DEFAULT_TAG)
            asset_attrs = {
                CFG_ASSET_DESC_KEY: asset_desc,
                CFG_ASSET_DEFAULT_TAG_KEY: default_tag,
            }
            _LOGGER.debug(f"Updating '{genome}/{asset_name}' asset attributes...")
            with write_lock(rgc_server) as r:
                r.update_assets(genome, asset_name, asset_attrs)
                r.write()

            tag = tag_list[counter] if tag_list is not None else None
            tags = tag or list(
                rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset_name][
                    CFG_ASSET_TAGS_KEY
                ].keys()
            )
            for tag_name in tags if isinstance(tags, list) else [tags]:
                if not rgc.is_asset_complete(genome, asset_name, tag_name):
                    raise MissingConfigDataError(
                        f"Asset '{genome}/{asset_name}:{tag_name}' is incomplete. "
                        f"This probably means an attempt to archive a partially "
                        f"pulled parent. refgenieserver archive requires all assets to "
                        f"be built prior to archiving."
                    )
                file_name = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset_name][
                    CFG_ASSET_TAGS_KEY
                ][tag_name][CFG_ASSET_PATH_KEY]
                target_file_core = os.path.join(target_dir, f"{asset_name}__{tag_name}")
                target_file = f"{target_file_core}.tgz"
                input_file = os.path.join(genome_dir, file_name, tag_name)
                # these attributes have to be read from the original RefGenConf in case the archiver just increments
                # an existing server RefGenConf
                parents = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset_name][
                    CFG_ASSET_TAGS_KEY
                ][tag_name].setdefault(CFG_ASSET_PARENTS_KEY, [])
                children = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset_name][
                    CFG_ASSET_TAGS_KEY
                ][tag_name].setdefault(CFG_ASSET_CHILDREN_KEY, [])
                seek_keys = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset_name][
                    CFG_ASSET_TAGS_KEY
                ][tag_name].setdefault(CFG_SEEK_KEYS_KEY, {})
                asset_digest = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset_name][
                    CFG_ASSET_TAGS_KEY
                ][tag_name].setdefault(CFG_ASSET_CHECKSUM_KEY, None)
                if not os.path.exists(target_file) or force:
                    _LOGGER.info(
                        f"Creating archive '{target_file}' from '{input_file}' asset"
                    )
                    try:
                        _copy_asset_dir(input_file, target_file_core)
                        _get_asset_dir_contents(target_file_core, asset_name, tag_name)
                        _check_tgz(input_file, target_file)
                        _copy_recipe(input_file, target_dir, asset_name, tag_name)
                        _copy_log(input_file, target_dir, asset_name, tag_name)
                        # TODO: remove the rest of this try block in the future
                        _check_tgz_legacy(
                            input_file,
                            target_file,
                            asset_name,
                            rgc.get_genome_alias_digest(alias=genome, fallback=True),
                            rgc.get_genome_alias(digest=genome, fallback=True),
                        )
                        _copy_recipe(input_file, alias_target_dir, asset_name, tag_name)
                        _copy_log(input_file, alias_target_dir, asset_name, tag_name)
                    except OSError as e:
                        _LOGGER.warning(e)
                        continue
                    else:
                        _LOGGER.info(
                            f"Updating '{genome}/{asset_name}:{tag_name}' tag attributes"
                        )
                        tag_attrs = {
                            CFG_ASSET_PATH_KEY: file_name,
                            CFG_SEEK_KEYS_KEY: seek_keys,
                            CFG_ARCHIVE_CHECKSUM_KEY: checksum(target_file),
                            CFG_ARCHIVE_SIZE_KEY: size(target_file),
                            CFG_ASSET_SIZE_KEY: size(input_file),
                            CFG_ASSET_PARENTS_KEY: parents,
                            CFG_ASSET_CHILDREN_KEY: children,
                            CFG_ASSET_CHECKSUM_KEY: asset_digest,
                        }
                        # TODO: legacy checksum generation and tag dictionary
                        #  update to be removed in the future
                        legacy_digest = checksum(
                            replace_str_in_obj(
                                target_file,
                                x=rgc.get_genome_alias_digest(
                                    alias=genome, fallback=True
                                ),
                                y=rgc.get_genome_alias(digest=genome, fallback=True),
                            )
                        )
                        tag_attrs.update(
                            {CFG_LEGACY_ARCHIVE_CHECKSUM_KEY: legacy_digest}
                        )
                        _LOGGER.debug(f"attr dict: {tag_attrs}")
                        with write_lock(rgc_server) as r:
                            for parent in parents:
                                # here we update any pre-existing parents' children
                                # attr with the newly added asset
                                _LOGGER.debug(
                                    f"Updating {parent} children list with "
                                    f"{genome}/{asset_name}:{tag_name}"
                                )
                                rp = parse_registry_path(parent)
                                parent_genome = rp["namespace"]
                                parent_asset = rp["item"]
                                parent_tag = rp["tag"]
                                try:
                                    r.seek(
                                        parent_genome,
                                        parent_asset,
                                        parent_tag,
                                        strict_exists=True,
                                    )
                                except RefgenconfError:
                                    _LOGGER.warning(
                                        f"'{genome}/{asset_name}:{tag_name}'s parent "
                                        f"'{parent}' does not exist, skipping relationship updates"
                                    )
                                    continue
                                r.update_relatives_assets(
                                    parent_genome,
                                    parent_asset,
                                    parent_tag,
                                    [f"{genome}/{asset_name}:{tag_name}"],
                                    children=True,
                                )
                            r.update_tags(genome, asset_name, tag_name, tag_attrs)
                            r.write()
                else:
                    exists_msg = f"'{target_file}' exists."
                    try:
                        rgc_server[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset_name][
                            CFG_ASSET_TAGS_KEY
                        ][tag_name][CFG_ARCHIVE_CHECKSUM_KEY]
                        _LOGGER.debug(exists_msg + " Skipping")
                    except KeyError:
                        _LOGGER.debug(exists_msg + " Calculating archive digest")
                        tag_attrs = {CFG_ARCHIVE_CHECKSUM_KEY: checksum(target_file)}
                        with write_lock(rgc_server) as r:
                            r.update_tags(genome, asset_name, tag_name, tag_attrs)
                            r.write()

        counter += 1
    _LOGGER.info(f"Builder finished; server config file saved: {rgc_server.file_path}")


def _check_tgz(path: str, output: str) -> None:
    """Check if file exists and tar it, using pigz if available.

    Args:
        path: Path to the file to be tarred.
        output: Path to the result file.

    Raises:
        OSError: If the file/directory to be archived does not exist.
    """
    pth, tag_name = os.path.split(path)
    if os.path.exists(path):
        # tar gzip the asset, exclude _refgenie_build dir, it may change digests
        cmd = "tar --exclude '_refgenie_build' -C {p} "
        cmd += (
            "-cvf - {tn} | pigz > {o}"
            if is_command_callable("pigz")
            else "-cvzf {o} {tn}"
        )
        command = cmd.format(p=pth, o=output, tn=tag_name)
        _LOGGER.info(f"command: {command}")
        run(command, shell=True)
    else:
        raise OSError(f"Entity '{path}' does not exist")


def _check_tgz_legacy(
    path: str, output: str, asset_name: str, genome_name: str, alias: str | list[str]
) -> None:
    """Legacy version of _check_tgz, to be removed in the future.

    Checks if file exists and tars it with alias-based naming. Uses pigz
    if available.

    Args:
        path: Path to the file to be tarred.
        output: Path to the result file.
        asset_name: Name of the asset.
        genome_name: Genome digest name.
        alias: Genome alias or list of aliases.

    Raises:
        OSError: If the file/directory to be archived does not exist.
    """
    # TODO: remove in the future
    if isinstance(alias, str):
        alias = [alias]
    for a in alias:
        if os.path.exists(path):
            aliased_output = replace_str_in_obj(output, x=genome_name, y=a)
            cmd = "rsync -rvL --exclude '_refgenie_build' {p}/ {p}/{an}/; "
            command = cmd.format(p=path, o=output, an=asset_name)
            _LOGGER.debug("command: {}".format(command))
            run(command, shell=True)
            swap_names_in_tree(os.path.join(path, asset_name), a, genome_name)
            # tar gzip the new dir
            cmd = "cd {p}; " + (
                "tar -cvf - {an} | pigz > {oa}; "
                if is_command_callable("pigz")
                else "tar -cvzf {oa} {an}; "
            )
            # remove the new dir
            cmd += "rm -r {p}/{an}; "
            command = cmd.format(p=path, oa=aliased_output, an=asset_name)
            _LOGGER.debug(f"command: {command}")
            run(command, shell=True)
        else:
            raise OSError(f"Entity '{path}' does not exist")


def _copy_log(input_dir: str, target_dir: str, asset_name: str, tag_name: str) -> None:
    """Copy the build log file.

    Args:
        input_dir: Path to the source directory.
        target_dir: Path to the destination directory.
        asset_name: Asset name.
        tag_name: Tag name.
    """
    log_path = f"{input_dir}/{BUILD_STATS_DIR}/{ORI_LOG_NAME}"
    if log_path and os.path.exists(log_path):
        run(
            "cp "
            + log_path
            + " "
            + os.path.join(target_dir, TEMPLATE_LOG.format(asset_name, tag_name)),
            shell=True,
        )
        _LOGGER.debug(f"Log copied to: {target_dir}")
    else:
        _LOGGER.warning(f"Log not found: {log_path}")


def _copy_asset_dir(input_dir: str, target_dir: str) -> None:
    """Copy the asset directory via rsync.

    Args:
        input_dir: Path to the source directory.
        target_dir: Path to the destination directory.
    """
    if input_dir and os.path.exists(input_dir):
        run(
            f"rsync -rvL --exclude '_refgenie_build' {input_dir}/ {target_dir}/",
            shell=True,
        )
        _LOGGER.info(f"Asset directory copied to: {target_dir}")
    else:
        _LOGGER.warning(f"Asset directory not found: {input_dir}")


def _get_asset_dir_contents(asset_dir: str, asset_name: str, tag_name: str) -> None:
    """Create a JSON file listing the unarchived asset directory contents.

    Args:
        asset_dir: Path to the asset directory.
        asset_name: Name of the asset.
        tag_name: Name of the tag.
    """
    asset_dir_contents_file_path = os.path.join(
        os.path.dirname(asset_dir),
        TEMPLATE_ASSET_DIR_CONTENTS.format(asset_name, tag_name),
    )
    files = [
        os.path.relpath(os.path.join(dp, f), asset_dir)
        for dp, dn, fn in os.walk(asset_dir)
        for f in fn
        if BUILD_STATS_DIR not in dp
    ]
    _LOGGER.debug(f"dir contents: {files}")
    with open(asset_dir_contents_file_path, "w") as outfile:
        dump(files, outfile)
    _LOGGER.info(
        f"Asset directory contents file created: {asset_dir_contents_file_path}"
    )


def _copy_recipe(
    input_dir: str, target_dir: str, asset_name: str, tag_name: str
) -> None:
    """Copy the build recipe file.

    Args:
        input_dir: Path to the source directory.
        target_dir: Path to the destination directory.
        asset_name: Asset name.
        tag_name: Tag name.
    """
    recipe_path = (
        f"{input_dir}/{BUILD_STATS_DIR}/"
        f"{TEMPLATE_RECIPE_JSON.format(asset_name, tag_name)}"
    )
    if recipe_path and os.path.exists(recipe_path):
        run("cp " + recipe_path + " " + target_dir, shell=True)
        _LOGGER.debug(f"Recipe copied to: {target_dir}")
    else:
        _LOGGER.warning(f"Recipe not found: {recipe_path}")


def _remove_archive(
    rgc: RefGenConf,
    registry_paths: list[dict],
    cfg_archive_folder_key: str = CFG_ARCHIVE_KEY,
) -> list[str]:
    """Remove archives and corresponding entries from the RefGenConf object.

    Args:
        rgc: Configuration object to remove entries from.
        registry_paths: Entries to remove.
        cfg_archive_folder_key: Archive folder key in the genome config file.

    Returns:
        List of removed file paths.
    """
    ret = []
    for registry_path in _correct_registry_paths(registry_paths):
        genome, asset, tag = (
            registry_path["namespace"],
            registry_path["item"],
            registry_path["tag"],
        )
        try:
            if asset is None:
                [
                    rgc.cfg_remove_assets(genome, x, None)
                    for x in rgc.list_assets_by_genome(genome)
                ]
            else:
                rgc.cfg_remove_assets(genome, asset, tag)
            _LOGGER.info(f"{genome}/{asset}{':' + tag if tag else ''} removed")
        except KeyError:
            _LOGGER.warning(
                f"{genome}/{asset}{':' + tag if tag else ''} not found and not removed"
            )
            continue
        ret.append(
            os.path.join(
                rgc[cfg_archive_folder_key],
                genome,
                f"{asset or '*'}__{tag or '*'}.tgz",
            )
        )
        for p in ret:
            archives = glob(p)
            for path in archives:
                try:
                    os.remove(path)
                except FileNotFoundError:
                    _LOGGER.warning(f"File does not exist: {path}")
        try:
            os.removedirs(os.path.join(rgc[cfg_archive_folder_key], genome))
            _LOGGER.info(f"Removed empty genome directory: {genome}")
        except OSError:
            pass
    return ret


def _correct_registry_paths(registry_paths: list[dict]) -> list[dict]:
    """Correct registry paths by swapping 'namespace' and 'item' keys.

    parse_registry_path recognizes 'item' as the central element, but we
    require 'namespace' to be central. This function swaps them.

    Args:
        registry_paths: Output of parse_registry_path.

    Returns:
        Corrected registry paths.
    """

    def _swap(rp: dict) -> dict:
        """Swap 'namespace' and 'item' values in a registry path dict.

        Args:
            rp: Dict to swap values for.

        Returns:
            Dict with swapped values.
        """
        rp["namespace"] = rp["item"]
        rp["item"] = None
        return rp

    return [_swap(x) if x["namespace"] is None else x for x in registry_paths]


def _get_paths_element(registry_paths: list[dict], element: str) -> list[str | None]:
    """Extract a specific element from a collection of registry paths.

    Args:
        registry_paths: Output of parse_registry_path.
        element: One of 'protocol', 'namespace', 'item', or 'tag'.

    Returns:
        List of extracted elements.
    """
    return [x[element] for x in _correct_registry_paths(registry_paths)]
