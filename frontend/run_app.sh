#!/bin/bash

THIS_SCRIPT=$(readlink -f "$0")
DIR_FRONT_END=$(dirname "$THIS_SCRIPT")
DIR_ROOT=$(cd $DIR_FRONT_END && cd .. && pwd)
DIR_BACKEND="${DIR_ROOT}/backend"
DIR_SCRIPTS=""

START_SERVER="${DIR_BACKEND}/start_server.sh"
echo -e $START_SERVER

function main(){
    flutter run -d Chrome
    PID_APP="$!"
    echo -e "PID APP: $PID_APP"
    #"$START_SERVER"
}

main "$@"
