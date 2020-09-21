#!/bin/bash

export CUDA_VISIBLE_DEVICES="-1"
bin=/home/smartcall/anaconda3/envs/rasa-1.9/bin

export SANIC_WORKERS=1

PATH_PID=resources/pid
PATH_LOG=resources/logs

if [ -f $PATH_PID/rasa_action.pid ] && [ $(cat $PATH_PID/rasa_action.pid | wc -w) -gt 0 ]; then
	echo "[ERROR] Rasa actions is still running at pid $(cat $PATH_PID/rasa_action.pid)!"
	echo "[ERROR] Please run ./kill_server.sh to shut it down"
	exit 1
fi

if [ -f $PATH_PID/rasa_server.pid ] && [ $(cat $PATH_PID/rasa_server.pid | wc -w) -gt 0 ]; then
    echo "[ERROR] Rasa server is still running at pid $(cat $PATH_PID/rasa_server.pid)!"
    echo "[ERROR] Please run ./kill_server.sh to shut it down"
    exit 1
fi

nohup $bin/rasa run actions -p 5014 --debug > $PATH_LOG/rasa_action.log &
pid_action=$(echo $!)
echo $pid_action > $PATH_PID/rasa_action.pid
echo "Started rasa actions - Log in $PATH_LOG/rasa_action.log - PID $pid_action"

nohup $bin/rasa run -m models --enable-api --cors "*" -p 6114 --debug > $PATH_LOG/rasa_server.log &
pid_server=$(echo $!)
echo $pid_server > $PATH_PID/rasa_server.pid
echo "Started rasa server - Log in $PATH_LOG/rasa_server.log - PID $pid_server"
