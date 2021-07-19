#!/bin/bash
#TODO: Create a var to store common arguments
INITPATH=$PWD/init.py

if [[ DEBUG -eq 1 ]]; then
    kopf run --liveness=http://0.0.0.0:8080/healthz -A "$INITPATH" --verbose
    # echo "debug"
elif [[ QUIET -eq 1 ]]; then
    kopf run --liveness=http://0.0.0.0:8080/healthz -A "$INITPATH" --quiet
    # echo "quiet"
else
    # echo "normal"
    kopf run --liveness=http://0.0.0.0:8080/healthz -A "$INITPATH"
fi