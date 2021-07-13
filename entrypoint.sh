#!/bin/bash
INITPATH=$PWD/init.py

if [[ DEBUG -eq 1 ]]; then
    kopf run -A "$INITPATH" --verbose
    # echo "debug"
elif [[ QUIET -eq 1 ]]; then
    kopf run -A "$INITPATH" --quiet
    # echo "quiet"
else
    # echo "normal"
    kopf run -A "$INITPATH" 
fi