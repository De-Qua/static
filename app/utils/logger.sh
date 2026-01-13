#!/bin/bash

# This script provides some logging functions.
# The code comes from here: https://www.cubicrace.com/2016/03/efficient-logging-mechnism-in-shell.html
# Moreover it will redirect all the stdout and stderr to the log file
# and it will add timestamp to both, this code come from here: https://serverfault.com/questions/103501/how-can-i-fully-log-all-bash-scripts-actions

ALLOWED_LEVELS=("DEBUG","INFO","WARNING","ERROR")

if [ -z "$2" ]
  then
    LEVEL=INFO
  else
    LEVEL="$2"
fi
if [ -z "$1" ]
  then
    SCRIPT_LOG=logs/SystemOut.log
  else
    SCRIPT_LOG="$1"
fi


case $LEVEL in
  debug|DEBUG)
    LEVEL=0 ;;
  info|INFO)
    LEVEL=10 ;;
  warning|WARNING)
    LEVEL=20 ;;
  error|ERROR)
    LEVEL=30 ;;
  [:digit:])
    LEVEL=$LEVEL ;;
  *)
    if [[ $LEVEL =~ ^[0-9]+$ ]]
      then
        LEVEL=$LEVEL
      else
        LEVEL=10
    fi ;;
esac

touch $SCRIPT_LOG

exec 3>&1 4>&2
trap 'exec 2>&4 1>&3' 0 1 2 3
exec 1>>$SCRIPT_LOG 2> >(./utils/predate.sh "STDERR")>&1

function SCRIPTENTRY(){
 timeAndDate=`date`
 script_name=`basename "$0"`
 script_name="${script_name%.*}"
 if [[ $LEVEL -le 10 ]]
   then
     echo "[$timeAndDate] [INFO]  > $script_name $FUNCNAME" >> $SCRIPT_LOG
 fi
}

function SCRIPTEXIT(){
 script_name=`basename "$0"`
 script_name="${script_name%.*}"
 if [[ $LEVEL -le 10 ]]
   then
     echo "[$timeAndDate] [INFO]  < $script_name $FUNCNAME" >> $SCRIPT_LOG
 fi
}

function ENTRY(){
 local cfn="${FUNCNAME[1]}"
 timeAndDate=`date`
 if [[ $LEVEL -le 10 ]]
   then
     echo "[$timeAndDate] [INFO]  > $cfn $FUNCNAME" >> $SCRIPT_LOG
 fi
}

function EXIT(){
 local cfn="${FUNCNAME[1]}"
 timeAndDate=`date`
 if [[ $LEVEL -le 10 ]]
   then
     echo "[$timeAndDate] [INFO]  < $cfn $FUNCNAME" >> $SCRIPT_LOG
 fi
}


function INFO(){
 local function_name="${FUNCNAME[1]}"
  local msg="$1"
  timeAndDate=`date`
  if [[ $LEVEL -le 10 ]]
    then
      echo "[$timeAndDate] [INFO]  $msg" >> $SCRIPT_LOG
  fi
}


function DEBUG(){
 local function_name="${FUNCNAME[1]}"
    local msg="$1"
    timeAndDate=`date`
  if [[ $LEVEL -le 0 ]]
    then
      echo "[$timeAndDate] [DEBUG]  $msg" >> $SCRIPT_LOG
  fi
}


function WARNING(){
 local function_name="${FUNCNAME[1]}"
  local msg="$1"
  timeAndDate=`date`
  if [[ $LEVEL -le 20 ]]
    then
      echo "[$timeAndDate] [WARNING]  $msg" >> $SCRIPT_LOG
  fi
}


function ERROR(){
 local function_name="${FUNCNAME[1]}"
    local msg="$1"
    timeAndDate=`date`
    if [[ $LEVEL -le 20 ]]
      then
    echo "[$timeAndDate] [ERROR]  $msg" >> $SCRIPT_LOG
  fi
}
