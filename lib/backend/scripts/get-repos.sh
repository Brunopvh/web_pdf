#!/usr/bin/env bash 
#

[[ -z $HOME ]] && HOME=~/

DIR_DOWN="$HOME/Downloads"
DIR_REPO="${DIR_DOWN}/repos"; mkdir -p "$DIR_REPO"


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

function get_repos(){

    local URLS=(
        "https://github.com/Brunopvh/web_pdf.git"
    )
    cd "$DIR_REPO"
    for u in "${URLS[@]}"; do
        pline
        echo -e "Cloando: $u"
        echo -e "Destino: $(pwd)"
        git clone $u
    done

}

function main(){

    get_repos

}

main $@

