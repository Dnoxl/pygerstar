#!/bin/bash

if [ "$1" == "gs" ]; then
    cd /home/daniel/bots/pygermanstarmarine
    python3 pygermanstarmarine.py &
elif [ "$1" == "dnm" ]; then
    cd /home/daniel/bots/PYDNoxMachina
    python3 PYDNoxMachina.py &
elif [ "$1" == "ds" ]; then
    cd /home/daniel/bots/depressionbot
    python3 depressionbot.py &
else
    echo "Invalid bot name. Please specify 'gs' or 'dnm'."
fi
