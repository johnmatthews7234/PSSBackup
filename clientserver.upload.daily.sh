#!/bin/bash
PATH=/Library/Frameworks/Python.framework/Versions/3.6/bin:/Library/Frameworks/Python.framework/Versions/2.7/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/X11/bin
SERVERNAME="surface-john"
SHARE="Client Server"
PLAYGROUND=$(security find-generic-password -a ${USER} -s $SERVERNAME -w)
if [-e $1.log]
then
	rm ./$1
fi
if [!-d ./$1]
then
	md ./$1
fi
mount_smbfs //${USER}:$PLAYGROUND@$SERVERNAME/$SHARE/$1 ./$1
python3 UploadFilesToDrive.py --Folder $1 --Path ./$1 --LogFile $1.log --RootFolder $SHARE






