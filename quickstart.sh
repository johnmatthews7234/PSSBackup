#!/bin/bash
if [ ! -d "./$1" ]
then
	mkdir "./$1"
fi
open smb://${USER}@$1/ "./$1"
PLAYGROUND=$(security find-internet-password -a ${USER} -s $1 -w)
python3 ./quickstart.py
