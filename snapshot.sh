#!/bin/bash
PATH=/Library/Frameworks/Python.framework/Versions/3.6/bin:/Library/Frameworks/Python.framework/Versions/2.7/bin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/X11/bin
python3 MakeSnapshot.py --Folder ACCOUNTS
python3 MakeSnapshot.py --Folder "Client Server"
python3 MakeSnapshot.py --Folder "PSS Server"

