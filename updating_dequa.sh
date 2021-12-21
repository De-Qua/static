#!/bin/bash
now=$(date + "%T")
cd /home/dequa/static
echo "starting", $now >> log.txt
conda activate dequa
echo "activated", $now >> log.txt
git pull
echo "pulled", $now >> log.txt
python3 update_everything.py
echo "updated", $now >> log.txt
# git push
