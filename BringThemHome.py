

import datetime
import logging
import os
import io
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from apiclient.http import MediaIoBaseDownload
import argparse


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
    try:
        file = service.files().create(body=file_metadata,
                                        fields='id').execute()
    except:
        return None
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
    try:
        results = service.files().list(
            q = query,
            fields = "files(id)").execute()
    except:
        results = None
    items = results.get('files',[])
    if not items:
        return MakeDriveDir(parentID, DirName)
    else:
        for item in items:
            return item.get('id')


def makeService():
    """
    Function: Make Drive API service.
    Purpose:  Hook into Drive API so we can send stuff up and down.
    Returns: API service
    """
    logging.debug("makeService")
    SCOPES = 'https://www.googleapis.com/auth/drive'
    store = file.Storage('credentials.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
        creds = tools.run_flow(flow, store)
    return build('drive', 'v3', http=creds.authorize(Http()))


def ScourFolderForFiles(FolderID, WorkingDirectory):
    """
    Function: ScourFolderForFiles
    Purpose: For each object in a Drive folder, work out what to do...
    param1: FolderID
    Type: id of Mime object application/vnd.google-apps.folder
    Returns: Nuffin.
    """
    logging.debug("::".join(("ScourFolderForFiles",FolderID)))
    directoryObject = os.path.dirname(WorkingDirectory + "\\")
    if not os.path.exists(directoryObject):
        os.makedirs(directoryObject)
    flag = False
    nextPageToken = None
    query = "'" + FolderID + "' in parents"
    while flag == False:
        results = service.files().list(
            q = query,
            fields = "nextPageToken, files(name, id, mimeType)",
            pageSize = 42 
            ).execute()
        items = results.get('files',[])
        nextPageToken = results.get('nextPageToken')
        if ((nextPageToken == None) or (not items)):
            flag = True
        for item in items :
            if item.get('mimeType') == "application/vnd.google-apps.folder" :
                ThisWorkingDirectory = "\\".join((WorkingDirectory,item.get('name')))
                ScourFolderForFiles(item.get('id'), ThisWorkingDirectory)
            else :
                GrabFile(item, WorkingDirectory)

def GrabFile(fileItem, WorkingDirectory):
    """
    Function: GrabFile
    Purpose: Determines which revision of a file to download.
    param1: fileItem
    Type: Drive File Object
    param2: WorkingDirectory
    Type: Path to drop file as string
    Return: Nuffin.
    """
    LatestDate= datetime.datetime.min
    logging.debug("::".join(("GrabFile",str(fileItem))))
    try :
        results = service.revisions().list(
            fileId = fileItem.get('id'), 
            fields = "revisions(id,modifiedTime)"
        ).execute()
    except:
        results = None 
    items = results.get('revisions',[])
    BestRevision = None
    for revision in items:
        RevisionDate= StringToTimeObject(revision.get('modifiedTime'))
        if (RevisionDate > LatestDate) and (RevisionDate < RestoreDate):
            BestRevision = revision
            LatestDate = RevisionDate
    if BestRevision:
        DownloadRevision(fileItem.get('id'),
	                        BestRevision.get('id'),
	                        fileItem.get('mimeType'),
	                        WorkingDirectory + "\\" + fileItem.get('name'))


def DownloadRevision(fileId, revisionId, mimeType, filename):
    """
    Function: DownloadRevision
    Purpose: Does the actual downloading of the file tree.
    param1: fileId
    Type: Drive file id as string
    param2: revisionId
    Type: Drive Revision id as string
    param3: mimeType
    Type: mimetype as string
    param4: filename
    Type: string
    """
    logging.debug("::".join(("DownloadRevision",fileId, revisionId, mimeType, filename)))
    if "google-apps" in mimeType:
        # skip google files
        return
    try:
        request = service.revisions().get_media(fileId=fileId, revisionId=revisionId)
        fh = io.FileIO(filename, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            done = downloader.next_chunk()
        logging.info("Downloaded " + filename)
    except:
        logging.info("Downloaded " + filename + " Failed")

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

def main():
    global RestoreDate
    defaultRestoreDate = TimeObjectToString(datetime.datetime.utcnow())
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--RestoreDirectory", help="Where to restore files to.")
    parser.add_argument("--RestoreDate", help="Date in past to restore from (RFC 3339 string)", default=defaultRestoreDate)
    parser.add_argument("--LogFile", help="Log File Name", default="BringThemHome.log")
    args = parser.parse_args()
    
    RestoreDate = args.RestoreDate
    
    logging.basicConfig(
    filename=args.LogFile,
    level=logging.DEBUG,
    format='%(asctime)s %(message)s')

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)

    global service
    service = makeService()
    CurrentWorkingDirectory = args.RestoreDirectory 

    rootDirId = GetDriveDirId(None, "PSSBackup")
    ScourFolderForFiles(rootDirId,CurrentWorkingDirectory)

if __name__ == '__main__' :
    main()
