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
    """
    Function: StringToTimeObject
    Purpose: To convert a Google RFC 3339 string to a datetime.datetime object
    param1: TimeString
    Type: String
    Output: datetime.datetime
    """
    logging.debug("::".join( ( "StringToTimeObject", TimeString ) ) )
    return datetime.datetime.strptime(TimeString, "%Y-%m-%dT%H:%M:%S.%fZ")

def TimeObjectToString(TimeObject):
    """
    Function: TimeObjectToString
    Purpose: To convert a datetime.datetime object to UTC RFC 3339 string
    param1: TimeObject
    Type: datetime.datetime
    Output: String
    """
    logging.debug("::".join( ("TimeObjectToString", str(TimeObject) ) ) )
    return datetime.datetime.strftime(TimeObject, "%Y-%m-%dT%H:%M:%S.%fZ")

def MakeDriveDir(parentID, name):
    """
    Function: MakeDriveDir
    Purpose: Create a Drive directory under a parentID
    param1: parentID
    Type: id of Mime object application/vnd.google-apps.folder OR None
    param2: name
    Type: String of name of folder to create
    Output: id of created folder.
    
    WeirdShit:  If None is specified it will try to make it in the root directory.
        Wherever that is...
    """
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
    Function: GetDriveDirId
    Purpose: Retrieve the id of a folder given the parent id and name of the
        folder
    param1: parentID
    Type: id of Mime object application/vnd.google-apps.folder
    param2: DirName
    Type: String Directory name
    Returns : id of Mime object application/vnd.google-apps.folder
    
    WeirdShit:  If the directory does not exist, creates same and returns the
        new id
    """
    logging.debug("::".join(("GetDriveDirId", str(parentID), DirName)))
    query = "( name = '" + DirName + "' ) and ( mimeType = 'application/vnd.google-apps.folder' )"
    if  parentID:
        query += " and ( '" + parentID + "' in parents )"
    try:
        results = service.files().list(
            q = query,
            fields = "files(id)").execute()
        items = results.get('files',[])
    except:
        pass
    if not items:
        return MakeDriveDir(parentID, DirName)
    else:
        for item in items:
            return item.get('id')


def uploadFile (parentID, path, fileName):
    """
    Function : uploadFile
    Purpose: Upload a file to Google Drive
    param1: parentID
    Type: id of Mime object application/vnd.google-apps.folder
    param2: path
    Type: pathlib.Path as string
    param3: pathlib.name as string
    Returns: Drive id or False
    
    Weird Shit: on failure returns False 
    
    """
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
        return False

def updateFile(fileID, fileName, filePath):
    """
    Function : updateFile
    Purpose: Updates a file to Google Drive
    param1: fileID
    Type: id of file on Drive
    param2: fileName
    Type: pathlib.name as string
    param3: pathlib.Path as string
    Returns: Drive Revision id
    
    Weird Shit: on failure returns None 
    """
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
    """
    Function: FileLastModifiedOnDrive
    Purpose: Return RFC 3339 date of when file was last altered on Drive
    param1: parentID
    Type: id of Mime object application/vnd.google-apps.folder OR None
    param2 : fileName
    Type : String of Filename
    Returns: String of RFC 3339 Date or False
    
    Weird Shit: parentID can be None in which case you get the first file 
        Google finds.  Returns False if nothing can be found, or system stuff up
    """
    logging.debug("::".join(("FileLastModifiedOnDrive", parentID, fileName)))
    query = "( name = '" + fileName + "' )"
    if parentID:
        query += " and ( '" + parentID + "' in parents )"
    try:
        results = service.files().list(
             q = query,
             fields = "files(id,modifiedTime)"
             ).execute()
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
    """
    Function: DealWithFile
    Purpose: Take a file and determine if it should be uploaded, updated, or
        ignored
    param1: parentID
    Type: id of Mime object application/vnd.google-apps.folder
    param2: fileObject 
    Type: pathlib.object pertaining to a file.
    Returns: None
    """
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
    """
    Function: MoveTreeToDrive
    Purpose: Cycle through all items in a path to determine if they are a File 
        or Directory and then treat appropriately.
    param1: parentID
    Type: id of Mime object application/vnd.google-apps.folder
    param2: dirpath
    Type: string of file Path
    Returns: Not a Saussage.
    
    """
    logging.debug("::".join(("MoveTreeToDrive", parentID, dirPath)))
    with os.scandir(dirPath) as it:
        for entry in it:
            if entry.is_file():
                DealWithFile(parentID, entry)
            if entry.is_dir():
                MoveTreeToDrive(GetDriveDirId(parentID, entry.name), entry.path)



def makeService():
    """
    Function: Make Drive API service.
    Purpose:  Hook into Drive API so we can send stuff up and down.
    Returns: API service
    """
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
    
