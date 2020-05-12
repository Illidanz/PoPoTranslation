import os
from hacktools import common


def run():
    infolder = "data/extract/M2F2/"
    outfolder = "data/extract_MOV/"

    common.logMessage("Extracting MOV...")
    if not os.path.isfile("jpsxdec\\jpsxdec.jar"):
        common.logError("jpsxdec not found")
        return
    common.makeFolder(outfolder)
    files = common.getFiles(infolder, ".MOV")

    for file in common.showProgress(files):
        folder = outfolder + file.replace(".MOV", "") + "/"
        common.makeFolder(folder)
        common.execute("java -jar jpsxdec\\jpsxdec.jar -f \"{mov}\" -i 0 -dir \"{outfolder}\"".format(mov=infolder + file, outfolder=folder), False)
        common.execute("java -jar jpsxdec\\jpsxdec.jar -f \"{mov}\" -i 0 -dir \"{outfolder}\" -vf png".format(mov=infolder + file, outfolder=folder), False)
    # Clear log files
    for log in common.getFiles(os.getcwd(), ".log"):
        if log != "/tool.log":
            os.remove(log[1:])
    common.logMessage("Done! Extracted", len(files), "files")
