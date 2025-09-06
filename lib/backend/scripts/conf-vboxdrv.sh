#!/usr/bin/env bash 
#
# configurações do virtualbox driver.

function msg(){
    echo -e "-------------------------------------------"
    echo -e " + $@"
    echo -e "==========================================="
}


function config_debian_utils(){

    sudo apt update

    msg "Instalando ... module-assistant build-essential libsdl-ttf2.0-0 dkms linux-headers-$(uname -r)"
    sudo apt install module-assistant build-essential dkms
    sudo apt install libsdl-ttf2.0-0
    sudo apt install linux-headers-$(uname -r)
    sudo m-a prepare
}

function config_fedora_utils(){

    sudo dnf install kernel-headers kernel-devel dkms elfutils-libelf-devel qt5-qtx11extras
}


function config_vboxdrv(){

    if [[ -f '/etc/init.d/vboxdrv' ]]; then
        msg "Executando ... /etc/init.d/vboxdrv setup"
        sudo /etc/init.d/vboxdrv setup
    elif [[ -f '/usr/lib/virtualbox/vboxdrv.sh' ]]; then
        msg "Executando ... /usr/lib/virtualbox/vboxdrv.sh setup"
        sudo /usr/lib/virtualbox/vboxdrv.sh setup
    fi

    msg "Executando ... /sbin/vboxconfig"
    sudo /sbin/vboxconfig

}


function main(){

    if [[ '/etc/debian_version' ]]; then
        config_debian_utils
    elif [[ -f '/etc/fedora-release' ]]; then
        config_fedora_utils
    fi

    config_vboxdrv

    msg "Adicionando ... $USER ao grupo vboxusers"
    sudo usermod -a -G vboxusers "$USER"

}

main $@

