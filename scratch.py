import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--Folder", help="Name of the folder on Google Drive")
parser.add_argument("--Path", help="Local Path to what you want backed up")
parser.add_argument("--LogFile", help="Log File Name", default=("BackupToDrive.log"))
parser.add_argument("-v", "--verbose" help="Make Output Verbose" action="store_true")
args = parser.parse_args()
print(args.Folder)

