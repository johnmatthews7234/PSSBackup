"""
Grabs a directory name and lists all files inside that directories and any
other directories it finds.

"""

from __future__ import print_function

import os
import datetime
import logging
import argparse
import pathlib
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from apiclient.http import MediaFileUpload


def StringToTimeObject(TimeString):
    logging.debug("::".join( ( "StringToTimeObject", TimeString ) ) )
    return datetime.datetime.strptime(TimeString, "%Y-%m-%dT%H:%M:%S.%fZ")

def TimeObjectToString(TimeObject):
    logging.debug("::".join( ("TimeObjectToString", str(TimeObject) ) ) )
    return datetime.datetime.strftime(TimeObject, "%Y-%m-%dT%H:%M:%S.%fZ")

def MakeDriveDir(parentID, name):
    logging.debug("::".join(("MakeDriveDir", str(parentID), name)))
    file_metadata = {
        'name'      : name,
        'mimeType'  : 'application/vnd.google-apps.folder'}
    if parentID:
        file_metadata['parents'] = [parentID]
    file = service.files().create(body=file_metadata,
                                        fields='id').execute()
    logging.info( "::".join( ( "Made Directory", name ) ) )
    return file.get('id')


def GetDriveDirId(parentID, DirName):
    """
    Put in a Parent ID or none
    Also put in a name of the directory
    outputs False on a non existing directory or drive ID if it does exist
    """
    logging.debug("::".join(("GetDriveDirId", str(parentID), DirName)))
    query = "( name = '" + DirName + "' ) and ( mimeType = 'application/vnd.google-apps.folder' )"
    if  parentID:
        query += " and ( '" + parentID + "' in parents )"
    results = service.files().list(
        q = query,
        fields = "files(id)").execute()
    items = results.get('files',[])
    if not items:
        return MakeDriveDir(parentID, DirName)
    else:
        for item in items:
            return item.get('id')


def uploadFile (parentID, path, fileName):
    logging.debug("::".join(("uploadFile", parentID, path, fileName)))
    try:
        file_metadata = {'name' : fileName,
                     'parents' : [parentID]}
        media = MediaFileUpload ( path )
        file = service.files().create(body = file_metadata,
                                        media_body = media,
                                        fields = 'id'
                                      ).execute()
        logging.info( "::".join( ( "Uploaded", path, fileName ) ) )
        return file.get('id')
    except:
        logging.error("::".join(("uploadFile", parentID, path, fileName, "Failed")))

def updateFile(fileID, fileName, filePath):
    logging.debug("::".join(("updateFile", fileID, fileName, filePath)))
    try :
        file_metadata = {'fileId'   : fileID}
        media = MediaFileUpload ( filePath )
        file = service.files().update(fileId = fileID,
                                    body = file_metadata,
                                    media_body = media,
                                    fields = 'id').execute()
        logging.info( "::".join( ( "Updated", filePath, fileName ) ) )
        return file.get('id')
    except :
        logging.error("::".join(("updateFile", fileID, filePath, fileName, "Failed")))

def FileLastModifiedOnDrive(parentID, fileName):
    logging.debug("::".join(("FileLastModifiedOnDrive", parentID, fileName)))
    query = "( name = '" + fileName + "' )"
    if parentID:
        query += " and ( '" + parentID + "' in parents )"
    results = service.files().list(
        q = query,
        fields = "files(id,modifiedTime)"
        ).execute()
    try:
        items = results.get('files',[])
    except:
        return False
    if not items:
        return False
    else:
        for item in items:
            return item
            break


def DealWithFile(parentID, fileObject):
    logging.debug("::".join(("DealWithFile", parentID, str(fileObject))))
    if not pathlib.Path(fileObject.path).exists():
        return
    LocalLastModified = datetime.datetime.utcfromtimestamp(os.path.getmtime(fileObject.path))
    if LocalLastModified < LastUpdate :
        return
    myFileOnDrive = FileLastModifiedOnDrive(parentID, fileObject.name)
    if not myFileOnDrive:
        uploadFile(parentID, fileObject.path, fileObject.name)
    else:
        if StringToTimeObject(myFileOnDrive.get('modifiedTime')) < LocalLastModified:
            updateFile(myFileOnDrive.get('id'), fileObject.name ,fileObject.path)
    return


def MoveTreeToDrive(parentID, dirPath):
    logging.debug("::".join(("MoveTreeToDrive", parentID, dirPath)))
    with os.scandir(dirPath) as it:
        for entry in it:
            if entry.is_file():
                DealWithFile(parentID, entry)
            if entry.is_dir():
                MoveTreeToDrive(GetDriveDirId(parentID, entry.name), entry.path)



def makeService():
    logging.debug( "makeService" )
    SCOPES = 'https://www.googleapis.com/auth/drive'
    store = file.Storage('credentials.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
        creds = tools.run_flow(flow, store)
    return build('drive', 'v3', http=creds.authorize(Http()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--Folder", help="Name of the folder on Google Drive")
    parser.add_argument("--Path", help="Local Path to what you want backed up")
    parser.add_argument("--LogFile", help="Log File Name", default=("BackupToDrive.log"))
    parser.add_argument("-v", "--Verbose", help="Make Output Verbose", action="store_true")
    parser.add_argument("-f", "--FullUpload", help="Ignore Date, and checks all files. (Will take longer)", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(
        filename=args.LogFile,
        level=logging.DEBUG,
        format='%(asctime)s %(message)s')
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    if args.Verbose :
        console.setLevel(logging.DEBUG)

    global service
    service = makeService()	

    global LastUpdate
    DateTimeFileName = (args.Folder + ".datetime")
    try:
        if pathlib.Path(DateTimeFileName).exists() :
            with open(DateTimeFileName) as f:
                LastUpdate = StringToTimeObject(f.read())
                f.closed
    except :
        pass
    if args.FullUpload:
        LastUpdate = datetime.datetime.min
    RightNowString = TimeObjectToString(datetime.datetime.utcnow())
    f = open(DateTimeFileName, 'w')
    f.write(RightNowString)
    f.close()
    rootDirId = GetDriveDirId(None, "PSSBackup")
    MoveTreeToDrive(GetDriveDirId(rootDirId, args.Folder), args.Path)

if __name__ == '__main__' :
    main()
    
