#!/usr/bin/env bash 
#

__appname__='INSTALLER UTILS'
[[ -z $HOME ]] && HOME=~/
DIR_DOWN="$HOME/Downloads"
APPS=(git wget curl python3 python3-venv openssh-server)

function print_line(){
    echo '-------------------------------------'
}

function msg(){
    print_line
    echo -e " + $@"
    print_line
}

function print(){
    echo -e "[$__appname__] $@"
}

function _install(){
    msg "instalando: ${APPS[@]}"
    for app in "${APPS[@]}"; do
        sudo apt install "$app" -y --download-only
    done
    sudo apt install "${APPS[@]}"
    sudo apt install libgl1-mesa-glx
    # sudo apt install libgtk2.0-dev
}

function main(){

    _install

}

main $@

