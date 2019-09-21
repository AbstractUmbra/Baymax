#!/bin/bash

# Needs to be root so sanity check:
if [[ $(id -u) != 0 ]];
    then
        echo "You are not root, please run this script as root."
        exit 1
fi

MoveFile(){
    if [[ -f "./RoboHz.service" ]];
        then
            if cp "./RoboHz.service" "/etc/systemd/system/RoboHz.service";
                then
                    chmod 0644 "/etc/systemd/system/RoboHz.service"
                else
                    echo "Cannot copy service to path, please check."
                    exit 1
            fi
        else
            echo "No service file found in current dir. Please check."
            exit 1
    fi
}

LoadService(){
    systemctl daemon-reload

    systemctl enable RoboHz

    systemctl start RoboHz
}

{
    MoveFile
    LoadService
} 2>&1