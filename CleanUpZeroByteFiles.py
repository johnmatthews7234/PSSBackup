import os
import argparse

def ScanThisDirectory(dirPath):
    with os.scandir(dirPath) as it:
        try:
            for entry in it:
                print(entry.path)
                if entry.is_file() and (os.stat(entry.name).st_size == 0):
                    print("::".join(("Removing", entry.path, entry.name)))
                    #os.remove(entry.name)
                if entry.is_dir():
                    ScanThisDirectory(entry.path)
        except:
            print("::".join(("Error in ", dirPath)))
                
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--Path", help="Root path to scan")
    args = parser.parse_args()
    ScanThisDirectory(args.Path)
    
if __name__ == '__main__' :
    main()
