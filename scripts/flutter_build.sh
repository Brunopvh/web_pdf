#!/bin/bash

__appname__='FLUTTER BUILD'
THIS_SCRIPT=$(readlink -f "$0")
THIS_DIR=$(dirname "$THIS_SCRIPT")
DIR_ROOT=$(cd "$THIS_DIR" && cd .. && pwd) # Raiz do projeto
DIR_FRONT="${DIR_ROOT}/frontend"
LIB_COMMON="${DIR_ROOT}/scripts/library/common.sh"
source "$LIB_COMMON" || exit 1


function print_line(){
	echo '---------------------------------------'
}

function print(){
	echo -e " [$__appname__] $@"
}

function print_err(){
	print_line
	echo -e " [$__appname__] Erro: $@"
}

function run_build(){
	print "Navegando para: $DIR_FRONT"
	cd "$DIR_FRONT" || return 1
	flutter build web --release || return 1
}

function copy_files(){
	# Copiar o conteúdo html para o diretório de hospedagem do nginx.
	cd "$DIR_FRONT"/build/web || return 1
	if [[ "${DIR_SITE_WWW}" == '/' ]]; then
		print_err "Diretório frontend inválido."
		return 1
	fi
	sudo mkdir -p "${DIR_SITE_WWW}" #/var/www/web_convert
	print "Copiando arquivos para: $DIR_SITE_WWW"
	sudo cp -r -u * "${DIR_SITE_WWW}"
}

function main(){
	if [[ ! -x $(command -v flutter) ]]; then
		print_err "Instale o flutter para prosseguir."
		return 1
	fi
	run_build || return 1
	copy_files
}

main "$@"