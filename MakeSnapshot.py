from __future__ import print_function


import datetime
import logging
import argparse
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools


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

def ScourFolderForFiles(FolderID):
    """
    Function: ScourFolderForFiles
    Purpose: For each object in a Drive folder, work out what to do...
    param1: FolderID
    Type: id of Mime object application/vnd.google-apps.folder
    Returns: Nuffin.
    """
    logging.debug("::".join(("ScourFolderForFiles",FolderID)))
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
        for item in items:
            if item.get('mimeType') == "application/vnd.google-apps.folder" :
                ScourFolderForFiles(item.get('id'))
            else :
                DoRevisionStuff(item.get('id'))
    

def RemoveExcess (items, numberOfExcess, fileID):
    """
    Function: RemoveExcess
    Purpose: Removes more than 150 keep forever revisions.
    param1: items 
    Type: array of Drive revisions
    param2: numberOfExcess
    Type: int 
    param3: fileID
    Type Drive id as string
    Returns: array of Drive revisions
    """
    logging.debug("::".join(("removeExcess",items, numberOfExcess, fileID)))
    sortedDates = []
    returnItems = []
    for item in items:
        sortedDates += item.get('modifiedTime')
    sortedDates = sorted(sortedDates)[0:numberOfExcess]
    for item in items:
        if item.get('modifiedTime') not in sortedDates:
            service.revisions().delete(
				fileId = fileID,
				revisionId = item.get('id')
			).execute()
        else :
            returnItems += item
        return returnItems


def DoRevisionStuff(fileID):
    """
    
    """
    logging.debug("::".join(("DoRevisionStuff",fileID)))
    filteredItems = []
    results = service.revisions().list(
        fileId = fileID, 
        fields = "revisions(id,modifiedTime,keepForever)"
        ).execute()
    items = results.get('revisions',[])
    if len(items) == 1:
        return
    for item in items:
        if item.get('keepForever'):
            filteredItems.append(item)
    if len(filteredItems) > 150:
        filteredItems = RemoveExcess(filteredItems, len(filteredItems) - 150, fileID )
        logging.info("Removed Excess revisions from " + fileID)

    for item in filteredItems:
        logging.debug(str(item))
        revisionDate = StringToTimeObject(item.get('modifiedTime'))
        if (revisionDate < timeLastWeek) and (revisionDate > timeTwoWeeksAgo ) and not item.get('keepForever'):
            revision_metadata = {'keepForever' : True}
            anotherResults = service.revisions().update(
                fileId = fileID,
                revisionId = item.get('id'),
                body = revision_metadata
                ).execute()
            logging.info("::".join(("Updated Revision",fileID,str(anotherResults))))
  
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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--Folder", help="Name pf the folder on Google Drive")
    parser.add_argument("--LogFile", help="Log File Name", default="MakeSnapshot.log")
    args = parser.parse_args()
    
    logging.basicConfig(
		filename=args.LogFile,
		level=logging.DEBUG,
		format='%(asctime)s %(message)s')

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)

    global service
    service = makeService()
    global timeLastWeek
    timeLastWeek = datetime.datetime.utcnow() - datetime.timedelta(days = 7)
    global timeTwoWeeksAgo
    timeTwoWeeksAgo = datetime.datetime.utcnow() - datetime.timedelta(days = 14)
    rootDirId = GetDriveDirId(None, "PSSBackup")
    ScourFolderForFiles(GetDriveDirId(rootDirId, args.Folder))

if __name__ == '__main__' :
    main()
        
