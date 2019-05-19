from const import CFG_GENOMES_KEY, CFG_FOLDER_KEY, CFG_ARCHIVE_KEY, TAR, TGZ
from subprocess import run
import os


def archive(rgc, args):
    """
    takes the refgenie.yaml config file and builds the individual tar archives
    that can be then served with 'refgenies serve'

    :param RefGenomeConfiguration rgc:
    :param argparse.Namespace args: arguments from the refgenies CLI
    """
    if args.force:
        print("build forced; file existence will be ignored")
    genomes = rgc.genomes_list()
    for genome in genomes:
        genome_dir = os.path.join(rgc[CFG_FOLDER_KEY], genome)
        target_dir = os.path.join(rgc[CFG_ARCHIVE_KEY], genome)
        genome_tarball = target_dir + TAR["ext"]
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        changed = False
        for asset_name, file_name in rgc.genomes[genome].items():
            target_file = os.path.join(target_dir, asset_name + TGZ["ext"])
            if not os.path.exists(target_file) or args.force:
                changed = True
                input_file = os.path.join(genome_dir, file_name)
                print("creating asset '{}' from '{}'".format(target_file, input_file))
                check_tar([input_file], target_file, TGZ["flags"])
            else:
                print("'{}' exists. Nothing to be done".format(target_file))
        if changed or not os.path.exists(genome_tarball):
            print("creating genome tarball '{}' from: {}".format(genome_tarball, genome_dir))
            check_tar([target_dir], genome_tarball, TAR["flags"])
    print("builder finished")


def check_tar(path, output, flags):
    """
    checks if file exists and tars it

    :param list[str] path: path to the file to be tarred
    :param str output: path to the result file
    :param str flags: tar command flags to use
    :return:
    """
    assert isinstance(flags, str), "flags are not string"
    assert isinstance(path, list), "path argument has to be a list"
    assert all(os.path.exists(x) for x in path), "one of the files ({}) does not exist".format(path)
    run("tar {} {} {}".format(flags, output, " ".join(path)), shell=True)
