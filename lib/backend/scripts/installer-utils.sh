#!/usr/bin/env bash 
#

[[ -z $HOME ]] && HOME=~/

DIR_DOWN="$HOME/Downloads"


function pline(){
    if [[ -z $1 ]]; then
        echo '-------------------------------------'
    elif [[ $1 == '=' ]]; then
        echo '====================================='
    fi

}

function msg(){
    pline
    echo -e " + $@"
    pline '='
}

function _install(){

    local APPS=(git wget curl python3 python3-venv openssh-server)
    msg "instalando: ${APPS[@]}"
    sudo apt install "${APPS[@]}"

}

function main(){

    _install

}

main $@

