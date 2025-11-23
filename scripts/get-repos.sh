#!/usr/bin/env bash 
#

[[ -z $HOME ]] && HOME=~/

URL_REPO='git@github.com:Brunopvh/web_pdf.git'
BRANCH='pbar'
DIR_DOWN="$HOME/GIT"
DIR_REPO="${DIR_DOWN}/${REPOS}" 
mkdir -p "$DIR_DOWN"

function print_line(){
    echo '-------------------------------------'

}

function msg(){
    print_line
    echo -e " + $@"
    print_line
}

function get_repos(){
    cd "$DIR_REPO"
    msg "Clonando ... $URL_REPO"
    git clone -b "$BRANCH" "$URL_REPO"
}

function main(){
    get_repos
}

main $@

