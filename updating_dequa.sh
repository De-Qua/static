#!/bin/bash

source ./utils/logger.sh "logs/log.out" DEBUG
#source ~/miniconda3/etc/profile.d/conda.sh

SCRIPTENTRY
DEBUG "Activate environment"
conda activate dequa
INFO "Starting the python update"
python3 update_everything.py
SCRIPTEXIT
# now=$(date + "%T")
# cd /home/dequa/static
# echo "starting $now" >> log.txt
# conda activate dequa
# echo "activated $now" >> log.txt
# git pull
# echo "pulled $now" >> log.txt
# python3 update_everything.py
# echo "updated $now" >> log.txt
# git push
