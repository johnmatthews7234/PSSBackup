#!/bin/bash
PATH=/Library/Frameworks/Python.framework/Versions/3.6/bin:/Library/Frameworks/Python.framework/Versions/2.7/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/X11/bin
rm ./ACCOUNTS.weekly.log
python3 UploadFilesToDrive.py --Folder ACCOUNTS --Path "/Volumes/ACCOUNTS/" --LogFile ACCOUNTS.weekly.log -f

