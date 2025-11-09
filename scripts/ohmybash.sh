#!/usr/bin/env bash 
#
# https://github.com/ohmybash/oh-my-bash
#
# cURL
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/ohmybash/oh-my-bash/master/tools/install.sh)"
#
# wGET
#   bash -c "$(wget https://raw.githubusercontent.com/ohmybash/oh-my-bash/master/tools/install.sh -O -)"
#
##############################################
# Manual Installation
#
# 1. Clone the repository:
# git clone https://github.com/ohmybash/oh-my-bash.git ~/.oh-my-bash
# 2. Optionally, backup your existing ~/.bashrc file:
# cp ~/.bashrc ~/.bashrc.orig
# 3. Create a new sh configuration file
# You can create a new sh config file by copying the template that we have included for you.
#
# cp ~/.oh-my-bash/templates/bashrc.osh-template ~/.bashrc
# 4. Reload your .bashrc
# source ~/.bashrc
#

[[ -z $HOME ]] && HOME=~/
readonly DIR_BACKUP=~/backups/bash
__appname__='INSTALL OHMYBASH'
# _hrs=$(date +%T | tr : -) _dt=$(date --iso-8601)
_backup_name="${DIR_BACKUP}/bashrc-$(date +%Y%m%d%H%M%S)"
_bash_theme='agnoster'
_local_repos=~/.oh-my-bash
_dir_bash_themes="${_local_repos}/themes"
_dir_tmp=~/tmp/repos
[[ -d "$_dir_tmp" ]] && rm -rf $_dir_tmp
mkdir -p "$_dir_tmp"
mkdir - "$_local_repos"
mkdir -p "$DIR_BACKUP"


function print_err(){
    echo -e '-----------------------------'
    echo -e " [$__appname__] Erro: $@"
}

function print(){
    echo -e " [$__appname__]: $@"
}

function bash_backup(){
    [[ ! -f "${HOME}/.bashrc" ]] && touch "${HOME}/.bashrc"
    [[ -f "$_backup_name" ]] && return 0
    print "Criando backup ... ${_backup_name}"
    cp "$HOME/.bashrc" "$_backup_name"
}

function _dow(){
    print "Clonando ohmybash em ... $_local_repos"
    git clone https://github.com/ohmybash/oh-my-bash.git "${_dir_tmp}" || {
        print_err "Falha ao baixar ohmybash";
        return 1;
    }
    print "Copiando arquivos para: $_local_repos"
    cd $_dir_tmp
    cp -r -u * "$_local_repos"
}

function install_theme(){
    print "Configurando thema $_bash_theme"
    sed -i "s|OSH_THEME=.*|OSH_THEME=$_bash_theme|g" "$HOME/.bashrc"
    return "$?"
}

function install_ohmybash(){
    cd "$_local_repos" || exit 1
    cd tools
    chmod +x install.sh
    ./install.sh
}

function exit_app(){
    print "Execute ... source ~/.bashrc"
}

function main(){
    clear
    bash_backup
    _dow || exit 1
    install_ohmybash
    install_theme
    exit_app
}

main $@

