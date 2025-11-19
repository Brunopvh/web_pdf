#!/bin/bash
#
# Intalar uma VENV loacal em sistemas Linux

THIS_FILE=$(readlink -f "$0")
THIS_DIR=$(dirname "$THIS_FILE")
DIR_ROOT=$(cd $THIS_DIR && cd .. && cd .. && pwd)
LIB_VENV="${DIR_ROOT}/scripts/library/common.sh" # Diretório contendo scripts em uma subpasta do projeto.
source "$LIB_VENV" || exit 1
FILE_REQ="${THIS_DIR}/$FILE_REQUIREMENTS"


function add_venv(){
	echo -e "Criando virtual-env em: $DIR_VENV"
	python3 -m venv "$DIR_VENV"
}

function config_venv(){
	source "$FILE_ACTIVATE" || exit 1
	echo -e "Instalando dependencias"
	pip3 install --upgrade pip
	[[ -f "$FILE_REQ" ]] && pip3 install -r "$FILE_REQ"
}

function main() {
  add_venv
  config_venv
}

main "$@"
