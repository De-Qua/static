#!/bin/bash
cd /home/dequa/static

git pull

python3 update_everything.py

git push
