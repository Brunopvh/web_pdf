#!/bin/bash
#
# versão 2025-09-30
#
# Este script clona o repositório online, atualiza o HTLM presente na subpasta web
# copiando os arquivos para /var/www/web_convert

THIS_APPNAME='ONLINE-RELEASE'
THIS_SCRIPT=$(readlink -f "$0")
THIS_DIR=$(dirname "$THIS_SCRIPT")
DIR_ROOT=$(cd "$THIS_DIR" && cd .. && pwd) # Raiz do projeto
LIB_COMMON="${DIR_ROOT}/scripts/library/common.sh"
source "$LIB_COMMON" || exit 1

readonly URL_PROJ='git@github.com:Brunopvh/web_pdf.git'
readonly BRANCH='pbar'
readonly TMP_DIR=~/tmp
readonly TMP_DOW="${TMP_DIR}/downloads"
readonly TMP_UN="${TMP_DIR}/unpack"
readonly  DIR_RELEASES="${TMP_DOW}/web_pdf/releases"
readonly TMP_FILE="${DIR_RELEASES}/web.zip"

[[ -d "$TMP_DOW" ]] && rm -rf "${TMP_DOW}"
[[ -d "$TMP_UN" ]] && rm -rf "${TMP_UN}"
mkdir -p "$TMP_DOW"
mkdir -p "$TMP_UN"

function print_err(){
    echo -e '-----------------------------'
    echo -e " [$THIS_APPNAME] Erro: $@"
}

function print(){
    echo -e " [$THIS_APPNAME]: $@"
}

function _download(){
    print "Baixando: $URL_PROJ"
    cd "$TMP_DOW"
    git clone -b "$BRANCH" "$URL_PROJ"
}

function _unpack(){
    print "Descompactando ... $TMP_FILE"
    cd "$DIR_RELEASES" || return 1
    unzip "$TMP_FILE" -d "$TMP_UN" 1> /dev/null
}

function _update(){
    _unpack || { print "a descompressão falhou"; return 1; }
    cd "$TMP_UN"
    print "Copiando arquivos de: $(pwd)\n$(ls)\n"
    sudo mkdir -p "${DIR_SITE_WWW}" #/var/www/web_convert
    sudo cp -r -u web/* "${DIR_SITE_WWW}" || return 1
}

function main(){
    if [[ ! -x $(command -v git) ]]; then
        print_err "Instale o GIT para prosseguir"
        exit 1
    fi

    _download || return 1
    _update || { print_err "Falha na atualização"; return 1; }
    print "Projeto atualizado"
}

main "$@"
