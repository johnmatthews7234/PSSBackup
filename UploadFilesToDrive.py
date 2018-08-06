"""
Grabs a directory name and lists all files inside that directories and any
other directories it finds.

"""

from __future__ import print_function

import os
import platform
import datetime
import logging
import argparse
import pathlib
import sqlite3
from apiclient.discovery import build
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


def GetDriveDirId(parentID, DirName, DirPath):
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
    logging.debug("::".join(("GetDriveDirId", str(parentID), DirName, DirPath)))

    # Try Database First    
    myCursor = sql.cursor()
    myData = (DirPath,)
    myCursor.execute('SELECT DriveObject FROM FolderTable WHERE FolderPath = ?', myData)
   
    result = myCursor.fetchone()
    if not (result == None ):
        return result[0]

    # Then Ask Drive
    query = "( name = '" + DirName + "' ) and ( mimeType = 'application/vnd.google-apps.folder' )"
    if  parentID:
        query += " and ( '" + parentID + "' in parents )"
    try:
        results = service.files().list(
            q = query,
            fields = "files(id)").execute()
        items = results.get('files',[])
    except:
        items = None
    if not items:
        return MakeDriveDir(parentID, DirName)
    else:
        for item in items:
            return item.get('id')

def creationDate(path):
    """
    Function: creationDate
    Purpose: Gets the date a file was created.
    param1: path
    Type: String path to file
    Returns: datetime.datetime
    """
    if platform.system() == 'Windows':
        return datetime.datetime.utcfromtimestamp(os.path.getctime(path))
    else:
        stat = os.path.getctime(path)
        try:
            return datetime.datetime.utcfromtimestamp(stat.st_birthtime)
        except AttributeError:
            return datetime.datetime.utcfromtimestamp(stat.st_mtime)

def uploadFile (parentID, myFileObject):
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
    logging.debug("::".join(("uploadFile", parentID, str(myFileObject))))
    try:
        file_metadata = {'name' : myFileObject.name,
                     'parents' : [parentID]}
        media = MediaFileUpload ( myFileObject.path )
        file = service.files().create(body = file_metadata,
                                        media_body = media,
                                        fields = 'id'
                                      ).execute()
        logging.info( "::".join( ( "Uploaded", myFileObject.path, myFileObject.name ) ) )
        myID = file.get('id')
        
        LocalLastModified = TimeObjectToString(datetime.datetime.utcfromtimestamp(os.path.getmtime(myFileObject.path)))
        #need to add date
        myCur = sql.cursor()
        myData = (myFileObject.path, myID, LocalLastModified,)
        myCur.execute('INSERT INTO FileTable (FilePath, id, modifiedTime) VALUES (?, ?, ? )', myData)
        sql.commit()
        return myID
    except:
        logging.error("::".join(("uploadFile", parentID, myFileObject.path, myFileObject.name, "Failed")))
        return False

def updateFile(fileID, fileObject):
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
    logging.debug("::".join(("updateFile", fileID, str(fileObject))))
    try :
        file_metadata = {'fileId'   : fileID}
        media = MediaFileUpload ( fileObject.path )
        file = service.files().update(fileId = fileID,
                                    body = file_metadata,
                                    media_body = media,
                                    fields = 'id').execute()
        logging.info( "::".join( ( "Updated", fileObject.path ) ) )
        myID = file.get('id')
        
        LocalLastModified = TimeObjectToString(datetime.datetime.utcfromtimestamp(os.path.getmtime(fileObject.path)))
        myCur = sql.cursor()
        myData = (myID, LocalLastModified)
        myCur.execute('UPDATE FileTable SET id = ?, modifiedTime = ?)', myData)
        sql.commit()
        return myID
    except :
        logging.error("::".join(("updateFile", fileID, str(fileObject), "Failed")))

def FileLastModifiedOnDrive(parentID, fileObject):
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
    logging.debug("::".join(("FileLastModifiedOnDrive", parentID, str(fileObject))))
    
    # Try Database First    
    myCursor = sql.cursor()
    myData = (fileObject.path,)
    myCursor.execute('SELECT modifiedTime, id FROM FileTable WHERE FilePath = ?', myData)
    result = myCursor.fetchone()
    if not (result == None):
        return result
       
    query = "( name = '" + fileObject.name + "' )"
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
            return (item.get('modifiedTime'), item.get('id'))
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
    
    myFileOnDrive = FileLastModifiedOnDrive(parentID, fileObject)
    if not myFileOnDrive:
        uploadFile(parentID, fileObject)
    else:
        if StringToTimeObject(myFileOnDrive[0]) < LocalLastModified:
            updateFile(myFileOnDrive[1] , fileObject)
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
                DirID = GetDriveDirId(parentID, entry.name, entry.path)
                myCur = sql.cursor()
                myData = (entry.path, DirID)
                myCur.execute('INSERT OR IGNORE INTO FolderTable (FolderPath, DriveObject) VALUES (?, ? )', myData)
                sql.commit()
                MoveTreeToDrive(GetDriveDirId(parentID, entry.name, entry.path), entry.path)



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
    service = build('drive', 'v3', http=creds.authorize(Http()))
    return service

def makeDatabase(myFolder):
    sqlConnection = sqlite3.connect(myFolder + '.db')
    sqlConnection.execute('''CREATE TABLE IF NOT EXISTS FileTable(ThisId INTEGER PRIMARY KEY AUTOINCREMENT,
        FilePath TEXT UNIQUE NOT NULL,
        modifiedTime TEXT NOT NULL,
        id TEXT UNIQUE NOT NULL)
    ''')
    
    sqlConnection.execute('''CREATE TABLE IF NOT EXISTS FolderTable(id INTEGER PRIMARY KEY AUTOINCREMENT,
        FolderPath TEXT UNIQUE NOT NULL,
        DriveObject TEXT UNIQUE NOT NULL)
    ''')
    return sqlConnection
    
    

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--Folder", help="Name of the folder on Google Drive")
    parser.add_argument("--Path", help="Local Path to what you want backed up")
    parser.add_argument("--LogFile", help="Log File Name", default=("BackupToDrive.log"))
    parser.add_argument("-v", "--Verbose", help="Make Output Verbose", action="store_true")
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
    global sql
    sql = makeDatabase(args.Folder)
    
    rootDirId = GetDriveDirId(None, "PSSBackup", args.Path + '..')
    MoveTreeToDrive(GetDriveDirId(rootDirId, args.Folder, args.Path), args.Path)
    sql.close()
    
    
if __name__ == '__main__' :
    main()
    
