#!/bin/bash
#
#
#

clear
THIS_SCRIPT=$(readlink -f "$0")
THIS_DIR=$(dirname "$THIS_SCRIPT")
DIR_ROOT=$(cd $THIS_DIR && cd .. && pwd)
LIB_VENV="${DIR_ROOT}/scripts/library/common.sh"
FILE_MAIN="${THIS_DIR}/server/main.py"
FILE_TEST="${THIS_DIR}/tests.py"
source "$LIB_VENV" || exit 1

echo -e "Ativando VEVN em: $FILE_ACTIVATE"
source "${FILE_ACTIVATE}" || exit 1

function main(){
    readonly PORT=5000
    echo -e "IP Servidor (hostname): $(hostname -I | cut -d ' ' -f 1)"
    uvicorn server:app --host 0.0.0.0 --port "$PORT"
}

main "$@"
