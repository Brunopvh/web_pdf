#!/bin/bash

THIS_FILE=$(readlink -f "$0")
THIS_DIR=$(dirname "$THIS_FILE")
DIR_ROOT=$(cd $THIS_DIR && cd .. && pwd)
LIB_VENV="${DIR_ROOT}/scripts/library/common.sh"
source "$LIB_VENV" || exit 1

echo -e "Ativando VEVN em: $FILE_ACTIVATE"
source "${FILE_ACTIVATE}" || exit 1

function main(){
    pip3 "$@"
}

main "$@"
