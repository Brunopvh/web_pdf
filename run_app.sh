#!/bin/bash

THIS_SCRIPT=$(readlink -f "$0")
DIR_OF_PROJECT=$(dirname "$THIS_SCRIPT")
FILE_SERVER="${DIR_OF_PROJECT}/lib/backend/run.sh"

function main(){
    echo -e "Ativando servidor"
    "$FILE_SERVER" &
    sleep 2
    echo -e "Executando Navegador"
    flutter run -d Chrome
}

main "$@"
