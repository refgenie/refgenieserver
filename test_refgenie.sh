#!/bin/bash

# Set up script
shopt -s expand_aliases
set -e
alias python=python3.6
# Work in virtual environment (requires virtualenv to be installed)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
export WORKDIR="$DIR/testing_refgenie"
export VENVDIR="$DIR/venv_refgenie"
# requires bulker to be installed
#python -m pip install --user --upgrade bulker

PROGNAME=$(basename $0)

ErrorExit()
{
	#
	# Function to handle error
	#	:param str 1: descriptive error message
	#
	echo "${PROGNAME}: ${1:-"Unknown Error"}" 1>&2
	# remove any created directories or files prior to exit
	if [ -d "$WORKDIR" ]; then
		rm -rf $WORKDIR
	fi
	if [ -d "$VENVDIR" ]; then
		rm -rf $VENVDIR
	fi
	exit 1
}

# activate bulker environment so you can build stuff (samtools etc)
# Requires BULKERCFG environment variable to be set
# Must load once before activating
#bulker load databio/refgenie:0.7.0
# [Must prevent bulker activate from creating a new shell](https://bulker.databio.org/en/dev/tips/#how-can-i-prevent-bulker-activate-from-creating-a-new-shell)
echo -e "\n-- Activate bulker --\n"
bulker-activate() {
  eval "$(bulker activate -e $@)"
}
bulker-activate databio/refgenie:0.7.2 || ErrorExit "$LINENO: Failed to activate bulker."

echo -e "\n-- Create and activate virtualenv --\n"
python -m venv $VENVDIR || ErrorExit "$LINENO: Failed to create virtual environment."
source $VENVDIR/bin/activate || ErrorExit "$LINENO: Failed to activate virtual environment."

# `refgenie` universe testing
mkdir $WORKDIR && cd $WORKDIR || ErrorExit "$LINENO: Failed to create working environment."

# install refgenie universe tools
python -m pip install --quiet wheel || ErrorExit "$LINENO: Failed to install wheel module."
python -m pip install --quiet https://github.com/databio/yacman/archive/dev.zip || ErrorExit "$LINENO: Failed to install development version of yacman."
python -m pip install --quiet https://github.com/databio/refgenconf/archive/dev.zip || ErrorExit "$LINENO: Failed to install development version of refgenconf."
python -m pip install --quiet https://github.com/databio/refgenie/archive/dev.zip || ErrorExit "$LINENO: Failed to install development version of refgenie."

echo -e "\n-- Create dockerfile --\n"
cat > testrgs.Dockerfile <<EOF
FROM tiangolo/uvicorn-gunicorn:python3.7-alpine3.8
LABEL authors="Nathan Sheffield, Michal Stolarczyk"

COPY . /app

RUN pip install https://github.com/databio/refgenconf/archive/dev.zip
RUN pip install https://github.com/databio/refgenieserver/archive/master.zip

EOF
if [ ! -f "$WORKDIR/testrgs.Dockerfile" ]; then
	ErrorExit "$LINENO: Failed to create test Dockerfile."
fi

echo -e "\n-- Build refgenieserver container --\n"
docker build -t testrgs --no-cache -f testrgs.Dockerfile . || ErrorExit "$LINENO: Failed to build refgenieserver container."

echo -e "\n-- Grab a small test asset --\n"
wget http://big.databio.org/example_data/rCRS.fa.gz || ErrorExit "$LINENO: Failed to retrieve test fastq file."

echo -e "\n-- Initialize refgenie --\n"
refgenie init -c refgenie_rCRS.yaml || ErrorExit "$LINENO: Failed to initialize refgenie."
refgenie init -c refgenie_test.yaml || ErrorExit "$LINENO: Failed to initialize refgenie."

echo -e "\n-- Build assets --\n"
refgenie build -c refgenie_rCRS.yaml -g rCRS -a fasta --files fasta=rCRS.fa.gz || ErrorExit "$LINENO: Failed to build rCRS asset."
refgenie build -c refgenie_test.yaml -g test -a fasta --files fasta=rCRS.fa.gz || ErrorExit "$LINENO: Failed to build test asset."

echo -e "\n-- Add genome_archive to refgenie config files --"
sed -i '' '1s;^;genome_archive: $WORKDIR/archive\
;' refgenie_rCRS.yaml
sed -i '' '1s;^;genome_archive: $WORKDIR/archive2\
;' refgenie_test.yaml

echo -e "\n-- Archive asset --\n"
docker run --user=$(id -u):$(id -g) -v $WORKDIR:$WORKDIR -e WORKDIR=`echo $WORKDIR` testrgs refgenieserver archive -c $WORKDIR/refgenie_rCRS.yaml || ErrorExit "$LINENO: Failed to archive rCRS asset."
docker run --user=$(id -u):$(id -g) -v $WORKDIR:$WORKDIR -e WORKDIR=`echo $WORKDIR` testrgs refgenieserver archive -c $WORKDIR/refgenie_test.yaml || ErrorExit "$LINENO: Failed to archive test asset."

echo -e "\n-- Run refgenieserver --\n"
docker run --rm -d -p 80:80 --name refgenieservercon -v $WORKDIR/archive:/genomes testrgs refgenieserver serve -c /genomes/refgenie_rCRS.yaml || ErrorExit "$LINENO: Failed to run rCRS refgenieserver."
docker run --rm -d -p 81:80 --name refgenieservercon2 -v $WORKDIR/archive2:/genomes testrgs refgenieserver serve -c /genomes/refgenie_test.yaml || ErrorExit "$LINENO: Failed to run test refgenieserver."

echo -e "\n-- Initialize multiserver refgenie config --\n"
mkdir pull_test || ErrorExit "$LINENO: Failed to create pull_test directory."
export REFGENIE=pull_test/refgenie_multiserver_testing.yaml
refgenie init -c $REFGENIE -s http://0.0.0.0:80 http://0.0.0.0:81 || ErrorExit "$LINENO: Failed to initialize multiserver refgenie yaml file."

echo -e "\n-- List all remote assets --\n"
refgenie listr -c $REFGENIE || ErrorExit "$LINENO: Failed to list remote assets."

echo -e "\n-- List rCRS remote assets --\n"
refgenie listr -c $REFGENIE -g rCRS || ErrorExit "$LINENO: Failed to list remote rCRS assets."
refgenie listr -c $REFGENIE -g test || ErrorExit "$LINENO: Failed to list remote test assets."

echo -e "\n-- Pull remote asset --\n"
refgenie pull -c $REFGENIE rCRS/fasta || ErrorExit "$LINENO: Failed to pull remote rCRS asset."
refgenie pull -c $REFGENIE test/fasta || ErrorExit "$LINENO: Failed to pull remote test asset."

echo -e "\n-- List local assets --\n"
refgenie list -c $REFGENIE || ErrorExit "$LINENO: Failed to list local assets."

echo -e "\n-- Shut down local servers --\n"
docker stop refgenieservercon || ErrorExit "$LINENO: Failed to stop remote rCRS server."
docker stop refgenieservercon2 || ErrorExit "$LINENO: Failed to stop remote test server."

echo -e "\n-- Deactivate the virtual environment --"
deactivate || ErrorExit "$LINENO: Failed to deactivate virtual environment."

echo -e "\n-- Clean up workspace --"
cd $DIR || ErrorExit "$LINENO: Failed to change to parent directory."
if [ -d "$WORKDIR" ]; then
	rm -rf $WORKDIR
fi
if [ -d "$VENVDIR" ]; then
	rm -rf $VENVDIR
fi

echo -e "\n-- DONE! --"
exit 0
