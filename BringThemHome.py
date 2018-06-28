#We want to restore shite

import datetime
import logging
import os
import io
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from apiclient.http import MediaFileUpload, MediaIoBaseDownload


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

def makeService():
    logging.debug("makeService")
    SCOPES = 'https://www.googleapis.com/auth/drive'
    store = file.Storage('credentials.json')
    creds = store.get()
    if not creds or creds.invalid:
        flow = client.flow_from_clientsecrets('client_secret.json', SCOPES)
        creds = tools.run_flow(flow, store)
    return build('drive', 'v3', http=creds.authorize(Http()))

def ScourFolderForFiles(FolderID, WorkingDirectory):
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
    LatestDate= datetime.datetime.min
    logging.debug("::".join(("GrabFile",str(fileItem))))
    filteredItems = []
    results = service.revisions().list(
        fileId = fileItem.get('id'), 
        fields = "revisions(id,modifiedTime)"
        ).execute()
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
    logging.debug("::".join(("DownloadRevision",fileId, revisionId, mimeType, filename)))
    if "google-apps" in mimeType:
        # skip google files
        return
    request = service.revisions().get_media(fileId=fileId, revisionId=revisionId)
    fh = io.FileIO(filename, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    logging.info("Downloaded " + filename)
		
	
def StringToTimeObject(TimeString):
    logging.debug("::".join( ( "StringToTimeObject", TimeString ) ) )
    return datetime.datetime.strptime(TimeString, "%Y-%m-%dT%H:%M:%S.%fZ")

def main():
    logging.basicConfig(
    filename='BringThemHome.log',
    level=logging.DEBUG,
    format='%(asctime)s %(message)s')

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)

    global service
    service = makeService()

    LocalRoot = "C:\\Temp"	
    CurrentWorkingDirectory = "\\".join((LocalRoot,"PSSBackup")) 

    rootDirId = GetDriveDirId(None, "PSSBackup")
    global RestoreDate
    RestoreDate = datetime.datetime.utcnow()
    ScourFolderForFiles(rootDirId,CurrentWorkingDirectory)

if __name__ == '__main__' :
    main()
