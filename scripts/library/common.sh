#!/bin/bash
#
#
# /etc/nginx/sites-available/
# sudo nano /etc/nginx/sites-available/flutter_web_pdf
#
# root /var/www/flutter_web_pdf;
#
# sudo chown -R www-data:www-data /var/www/flutter_web_pdf
# sudo chmod -R 755 /var/www/flutter_web_pdf
#
# SYSTEMCTL
# sudo systemctl start nginx
# sudo systemctl enable nginx
#
# REINICIAR
# sudo nginx -t; sudo systemctl restart nginx
# 
# CRIAR LINK SIMBOLICO
# sudo ln -s /etc/nginx/sites-available/meu_site /etc/nginx/sites-enabled/
#
#
#
# ARQUIVO DE CONFIGURAÇÃO NGIX: /etc/nginx/nginx.conf
# ARQUIVO DE CONFIGURAÇÃO DOS SITES: /etc/nginx/sites-available/
#

#=======================================================#
# Variaveis de ambiente para o virtualenv do projeto
#=======================================================#
readonly VENV_NAME='web'
readonly PREFIX_VENV="var/${VENV_NAME}"
readonly DIR_VENV="${HOME}/${PREFIX_VENV}"
readonly FILE_ACTIVATE="$DIR_VENV/bin/activate"
readonly FILE_REQUIREMENTS="requirements.txt"


#=======================================================#
# Variaveis para informações do projeto
#=======================================================#
readonly PROJ_NAME="web_convert"
readonly DIR_AVAILABLE="/etc/nginx/sites-available"
readonly DIR_ENABLE='/etc/nginx/sites-enabled'
readonly FILE_SITE_PROXY="${DIR_AVAILABLE}/${PROJ_NAME}" # sudo nano /etc/nginx/sites-enabled/web_convert
#readonly FILE_SITE_PROXY=~/Downloads/Teste.txt
readonly RELATIVE_DIR_ASSETS="frontend/assets"
readonly RELATIVE_FILE_JSON="data/ips.json" # Informações sobre IPS e rotas
readonly DIR_WWW="/var/www"
readonly DIR_SITE_WWW="${DIR_WWW}/${PROJ_NAME}" # Arquivos html e outros.

