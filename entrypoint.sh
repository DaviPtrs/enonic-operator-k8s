#!/bin/bash
INITPATH=$PWD/init.py
COMMON="kopf run --liveness=http://0.0.0.0:8080/healthz -A $INITPATH"

if [[ DEBUG -eq 1 ]]; then
    $COMMON --verbose
elif [[ QUIET -eq 1 ]]; then
    $COMMON --quiet
else
    $COMMON
fi