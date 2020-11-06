#!/bin/bash
INITPATH=$PWD/init.py

if [[ DEBUG -eq 1 ]]; then
    kopf run "$INITPATH" --verbose
    # echo "debug"
elif [[ QUIET -eq 1 ]]; then
    kopf run "$INITPATH" --quiet
    # echo "quiet"
else
    # echo "normal"
    kopf run "$INITPATH" 
fi