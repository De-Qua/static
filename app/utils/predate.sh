#!/bin/bash

# This function is to append time to the strings that goes in the logs
# explained here: https://stackoverflow.com/questions/1507674/how-to-add-timestamp-to-stderr-redirection

if [ -z "$1" ]
  then
    log_type="LOG"
  else
    log_type="$1"
fi

while read line ; do
    echo "[$(date)] [$log_type] ${line}"
done
