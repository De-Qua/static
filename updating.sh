#!/bin/bash
cd /home/dequa/static

conda activate dequa

sudo git pull

python3 update_everything.py

# git push
