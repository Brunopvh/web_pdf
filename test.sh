#!/bin/bash

THIS_SCRIPT=$(readlink -f "$0")
THIS_DIR=$(dirname "$THIS_SCRIPT")
FILE_MAIN="${THIS_DIR}/local-test.py"
LIB_VENV="${THIS_DIR}/backend/lib_venv.sh"


FILE='/home/brunoc/Downloads/OUTROS/INPUT/CARTAS/3.pdf'

curl -X POST http://192.168.100.47/uploads/pdf/join -F "file=@$FILE" -v

