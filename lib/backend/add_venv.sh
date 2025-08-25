#!/bin/bash
#
# Intalar uma VENV loacal em sistemas Linux

THIS_FILE=$(readlink -f "$0")
THIS_DIR=$(dirname "$THIS_FILE")
LIB_VENV="${THIS_DIR}/lib_venv.sh"
FILE_REQ="${THIS_DIR}/requirements.txt"
source "$LIB_VENV" || exit 1

function add_venv(){
	python3 -m venv "$DIR_VENV"
}

function config_venv(){
	source "$FILE_VENV" || exit 1
	pip3 install --upgrade pip
	[[ -f "$FILE_REQ" ]] && pip3 install -r "$FILE_REQ"
}

function main() {
  add_venv
  config_venv
}

main "$@"
