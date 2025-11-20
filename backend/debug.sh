#!/bin/bash
#
#
#

clear
THIS_SCRIPT=$(readlink -f "$0")
THIS_DIR=$(dirname "$THIS_SCRIPT")
DIR_ROOT=$(cd $THIS_DIR && cd .. && pwd)
LIB_VENV="${DIR_ROOT}/scripts/library/common.sh"
FILE_TEST="${THIS_DIR}/teste.py"
source "$LIB_VENV" || exit 1

echo -e "Ativando VEVN em: $FILE_ACTIVATE"
source "${FILE_ACTIVATE}" || exit 1

function main(){
    python3 "$FILE_TEST"
}

main "$@"
