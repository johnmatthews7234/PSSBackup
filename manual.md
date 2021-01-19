# ERMEGERDERP

# the PSS Backup Solution

## Introduction

When Champions of Change was engaged by Paper Stone Scissors to manage their ICT systems, one of the missing components was Disaster Recovery.  Since there was a pressing need for this,  John Matthews of Champions wrote a series of scripts to back up and restore their corporate data.

This is their story.

## Prerequisites.

Although this was designed to be as portable as possible, these instructions will be written for MacOS 10.13 Sierra

* [Python 3.6](https://www.python.org/downloads/release/python-360/)  Other versions may work, but it has been tested against this one.
* An account with at least readonly access to the data to be backed up
* Access to the itsupport@paperstonescissors.com account
* The scripts of helpfulness.  [PSSBackup](https://github.com/johnmatthews7234/PSSBackup)
* You will also need the client_secret.json file.  This is available from [John Matthews](mailto:john.matthews72@gmail.com)  You can keep the file in a safe location.  This works as a permissions contract between John and you.  By using it you declare that you trust John, and that you are confident in the code.  To aid you in this, all the code is human readable, so you can read it and see what I am doing.

## Setup

### Install Python

Pretty much follow the directions on the packet.  After the install, some addon libraries will have to be installed.  Open the terminal and type the following commands

	pip3 install datetime
	pip3 install argparse
	pip3 install pathlib
	pip3 install apiclient
	pip3 install httplib2
	pip3 install oauth2client
	pip3 install google-api-python-client
	
Now the python files have enough to run on.  You can now run 

	python3 ./quickstart.py

Then for no reason a web page will open asking you to log on to Drive.  Enter the following:-

* Log on name that has write access to drive e.g. john @johnmatthews.biz
* Password (I ain't tellin you that in this document)
* Permissions (Allow.)

This sets up permissions for the script to write to Google Drive.



	python3 UploadFilesToDrive.py --help
	usage: UploadFilesToDrive.py [-h] [--Folder FOLDER] [--Path PATH]
                             [--LogFile LOGFILE] [-v] [--Blacklist BLACKLIST]
                             [--RootFolder ROOTFOLDER]
	optional arguments:
  	-h, --help            show this help message and exit
	--Folder FOLDER       Name of the folder on Google Drive
	--Path PATH           Local Path to what you want backed up
	--LogFile LOGFILE     Log File Name
	-v, --Verbose         Make Output Verbose
	--Blacklist BLACKLIST
                        File containing folders to not back up
	--RootFolder ROOTFOLDER
                        Name of folder in Google Drive\PSSBackup containing
                        folder list

What was I thinking?  Help?  But we are'nt quite ready yet.  First we need to ensure we have any network drives mapped.  To help sort this out, we need to:-

### Prepare helper scripts

* Open the Keychain App
* Find the entry for the server we want to back up.
* Select "Access Control"
* Select "Allow all applications to access this item"
* Select "Save Changes"
* Enter your password and select "Allow"

You can now close keychain, because we can access the password we need to connect to the server.

Once this is done, we may need to do some quick and dirty editing of a helper script called "update.daily.sh".  Back to the terminal we go.

	cp update.daily.sh ClientServer.daily.sh
	chmod 755 ClientServer.daily.sh
	nano ClientServer.daily.sh
	
Now we should be staring at the worlds worst text editor.  Alter the SERVERNAME and SHARE variables to match the environment you want to back up. and hit Ctrl-X  then Y to save and exit.

Now we are attached to the file we want to back up, we can run the command

	python3 UploadFilesToDrive.py --Folder ClientServer --Path "/Volumes/Client Server" --LogFile ClientServer.log -v &

This will show you a couple of numbers and drop you back to the prompt.  
If this is the first time you are running this then the following files will be created.

* ClientServer.log
* ClientServer.db
* credentials.json

To watch what is going on type 

	tail -f ClientServer.log

To exit again, press Control-C

if you are happy with this then you can kill the job and we can sort out something more permenant.  There is a really good article on crontab [here](https://ole.michelsen.dk/blog/schedule-jobs-with-crontab-on-mac-osx.html).  But here is the gist of it.

	kill %1
	env EDITOR=nano crontab -e

Again, worlds worst text editor, and here is an example of one I brewed earlier.

	XMAILTO=""
	0 21 * * 0-6 cd ~/Documents/PSSBackup && ./ClientServer.daily.sh "_Master Job Folder Template"
	30 21 * * 0-6 cd ~/Documents/PSSBackup && ./ClientServer.daily.sh "_Stock Image Library"
	0 22 * * 0-6 cd ~/Documents/PSSBackup && ./ClientServer.daily.sh "Asahi"
	30 22 * * 0-6 cd ~/Documents/PSSBackup && ./ClientServer.daily.sh "Avari Capital Partners"
	0 23 * * 0-6 cd ~/Documents/PSSBackup && ./ClientServer.daily.sh "Baileys of Glenrowan"
	
Again Ctrl-X and Y to exit and save.  What this does, is every half hour from 9 pm every day we run the script against a named directory.  If it doesn't finish in time, then the next job runs at the same time.  If it does finish, then the computer gets a well earned break.

Now comes the check of progress.
