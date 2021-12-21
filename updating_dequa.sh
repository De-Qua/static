#!/bin/bash
cd /home/dequa/static
echo "starting" > log.txt
conda activate dequa
echo "activated" > log.txt
git pull
echo "pulled" > log.txt
python3 update_everything.py
# git push
