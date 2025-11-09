#!/bin/bash
#
# Este script instala o ngnix em sistemas de base Debian e configura o servidor Web deste projeto.
#
#
#
#
#
#
THIS_APPNAME='CONFIG NGINX'
THIS_SCRIPT=$(readlink -f "$0")
THIS_DIR=$(dirname "$THIS_SCRIPT")
DIR_ROOT=$(cd "$THIS_DIR" && cd .. && pwd) # Raiz do projeto
LIB_COMMON="${DIR_ROOT}/scripts/library/common.sh"
source "$LIB_COMMON" || exit 1

DIR_ASSETS="$DIR_ROOT/${RELATIVE_DIR_ASSETS}" # Flutter Assets no frontend
FILE_JSON_IPS="$DIR_ASSETS/${RELATIVE_FILE_JSON_IPS}" # Arquivo .json com ips e rotas
FILE_CONFIG_SITE="${DIR_AVAILABLE}/$PROJ_NAME"
DIR_BACKUP=~/backups/nginx
mkdir -p "$DIR_BACKUP"

[[ ! -d "$DIR_SITE_WWW" ]] && sudo mkdir -p "$DIR_SITE_WWW"
[[ ! -d "$DIR_AVAILABLE" ]] && sudo mkdir -p "$DIR_AVAILABLE"
[[ ! -d "$DIR_ENABLE" ]] && sudo mkdir -p "$DIR_ENABLE"

function print_err(){
	echo -e '-----------------------------'
	echo -e " [$THIS_APPNAME] Erro: $@"
}

function print(){
	echo -e " [$THIS_APPNAME]: $@"
}

#========== INSTALAÇÃO DO NGINX ===================#
function permission(){
	sudo chown -R www-data:www-data "${DIR_SITE_WWW}"
	sudo chmod -R 755 "${DIR_SITE_WWW}"
}

function install_nginx(){
	sudo apt update #&& sudo apt upgrade
	sudo apt install nginx ufw -y || return 1
	return 0
}

function config_firewall(){
	print "Configurando firewall"
	sudo ufw allow 'Nginx HTTP' 
	sudo ufw enable
	sudo ufw allow 8080/tcp
	sudo ufw status
}


#========== CONFIGURAÇÃO DO PROJETO ===================#

function get_ip_server(){
    grep 'ip_server' "$FILE_JSON" | cut -d ' ' -f 6 | sed 's/,//; s/"//g'
}

function get_rt_join_pdf(){
    grep 'rt_join_pdf' "$FILE_JSON" | cut -d ' ' -f 6 | sed 's/,//; s/"//g'
}

function get_rt_split_pdf(){
    grep 'rt_split_pdf' "$FILE_JSON" | cut -d ' ' -f 6 | sed 's/,//; s/"//g'
}

read -r -d "" SITE_CONF_NGINX <<EOF
server {
    listen 0.0.0.0:80;
    server_name $(hostname -I | cut -d ' ' -f 1);
    client_max_body_size 100M;

    # Servir o frontend (rotas estáticas)
    location / {
        root /var/www/$PROJ_NAME;
        try_files \$uri \$uri/ /index.html;
    }

    # Adicionar o proxy reverso para o backend
    location /uploads/pdf/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF


function create_conf_nginx(){
	# Criar o arquivo de configuração do site/projeto.
	local hrs=$(date | cut -d ' ' -f 5 | tr : -)
	local dt=$(date --iso-8601)
    local FILE_BAK="${DIR_BACKUP}/${PROJ_NAME}_${dt}-${hrs}"
    
    if [[ -f "$FILE_SITE_PROXY" ]]; then
        print "Criando backup: ${FILE_BAK}"
        cp -u "$FILE_SITE_PROXY" "$FILE_BAK"
    fi
    print "Gerando  arquivo de configuração: $FILE_SITE_PROXY"
    echo "$SITE_CONF_NGINX" | sudo tee "$FILE_SITE_PROXY"
}


function main(){
	install_nginx || { print_err "Falha ao tentar instalar NGINX"; return 1; }
	config_firewall || { print_err "Falha ao tentar configurar o firewall"; return 1; }
	create_conf_nginx
    print "Criando link ${DIR_ENABLE}/${PROJ_NAME}"
    sudo ln -sf "$FILE_SITE_PROXY" "${DIR_ENABLE}/${PROJ_NAME}"
}

main "$@"
