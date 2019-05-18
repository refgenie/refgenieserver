from .const import CFG_GENOMES_KEY, BASE_FOLDER
from refgenconf import select_genome_config
from yacman import load_yaml
from subprocess import run
import os
from shutil import rmtree


# TODO: dont stop at genomes level, check for assets and add if not available. leave the force option?
def archive(args):
    cfg_file = select_genome_config(args.config)
    # print("got config: {}".format(cfg_file))
    # print("got genomes: {}".format(args.genome))
    cfg = load_yaml(cfg_file)
    for k, v in cfg[CFG_GENOMES_KEY].items():
        if args.genome is not None and k not in args.genome:
            print("'{}' not in: '{}'. Skipping".format(k, ", ".join(args.genome)))
            continue
        genome_dir = os.path.join(BASE_FOLDER, k)
        if args.force or not os.path.exists(genome_dir) or args.genome is not None:
                if args.force or args.genome is not None:
                    print("Forced build; recreating dir: '{}'".format(genome_dir))
                    rmtree(genome_dir)
                os.makedirs(genome_dir)
                outputs = []
                for n, f in v.items():
                    output = os.path.join(genome_dir, n + ".tgz")
                    input_file = os.path.join(k, f)
                    print("creating '{}' from '{}'".format(output, input_file))
                    outputs.append(check_tar([input_file], output, "-cvzf"))
                print("creating parent tarball '{}.tar' from: {}".format(genome_dir, ", ".join(outputs)))
                check_tar(outputs, genome_dir + ".tar", "-cvf")
        else:
            print("'{}' exists. Nothing to be done".format(genome_dir))


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
    return output
