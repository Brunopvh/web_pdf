#!/bin/bash

THIS_SCRIPT=$(readlink -f "$0")
THIS_DIR=$(dirname "$THIS_SCRIPT")
FILE_MAIN="${THIS_DIR}/server.py"
FILE_TEST="${THIS_DIR}/tests.py"

LIB_VENV="${THIS_DIR}/lib_venv.sh"
source "${LIB_VENV}" || exit 1
echo '--------------------------------------'
echo -e "Ativando VEVN em: $FILE_VENV"
source "${FILE_VENV}" || exit 1

function main(){
    pip install -r "$THIS_DIR"/requirements.txt
}

main "$@"
