#!/bin/bash
#
# Ativa uma venv com as instruções presentes em: scripts/library/common.sh
# e disponibiliza comandos pip
#
THIS_FILE=$(readlink -f "$0")
THIS_DIR=$(dirname "$THIS_FILE")
DIR_ROOT=$(cd $THIS_DIR && cd .. && cd .. && pwd)
LIB_VENV="${DIR_ROOT}/scripts/library/common.sh"
source "$LIB_VENV" || exit 1

echo -e "Ativando VEVN em: $FILE_ACTIVATE"
source "${FILE_ACTIVATE}" || exit 1
function main(){
    pip3 "$@"
}

main "$@"
