import codecs
import os
import game
from hacktools import common


def extractFile(f, range, filename):
    f.seek(range.start)
    common.makeFolders(os.path.dirname(filename))
    with common.Stream(filename, "wb") as fout:
        fout.write(f.read(range.end - range.start))


def run():
    infolder = "data/extract/"
    outfile = "data/dat_output.txt"
    outscript = "data/extract_SCRIPT/"
    outimg = "data/extract_IMG/"
    outother = "data/extract_OTHER/"

    common.logMessage("Extracting DAT...")
    common.makeFolder(outscript)
    common.makeFolder(outimg)
    common.makeFolder(outother)
    files = common.getFiles(infolder, [".DAT", ".VIN"])
    with codecs.open(outfile, "w", "utf-8") as out:
        for file in common.showProgress(files):
            if "/SOUND" in file:
                continue
            common.logDebug("Processing", file)
            extension = os.path.splitext(file)[1]
            stringranges, imgranges, otherranges = game.getDatRanges(infolder + file, extension)
            with common.Stream(infolder + file, "rb") as f:
                # Extract script and strings
                for i in range(len(stringranges)):
                    stringrange = stringranges[i]
                    scriptfile = file.replace(extension, "_" + str(i).zfill(3))
                    extractFile(f, stringrange, outscript + scriptfile + ".bin")
                    detectfunc = game.detectEncodedString if stringrange.type != 1 else game.detectVINString
                    strings, positions = common.extractBinaryStrings(infolder + file, (stringrange.start, stringrange.end), detectfunc)
                    if len(strings) > 0:
                        common.logDebug("Processing script file", scriptfile, vars(stringrange))
                        out.write("!FILE:" + scriptfile + "\n")
                        for j in range(len(strings)):
                            # out.write("S" + str(stringrange.type) + "!")
                            out.write(strings[j] + "=\n")
                # Extract TIMs
                for i in range(len(imgranges)):
                    imgrange = imgranges[i]
                    timfile = file.replace(extension, "_" + str(i).zfill(3) + ".tim")
                    common.logDebug("Extracting TIM", timfile, vars(imgrange))
                    extractFile(f, imgrange, outimg + timfile)
                # Extract OTHERs
                for i in range(len(otherranges)):
                    otherrange = otherranges[i]
                    otherfile = file.replace(extension, "_" + str(i).zfill(3) + ".bin")
                    common.logDebug("Extracting OTHER", otherfile, vars(otherrange))
                    extractFile(f, otherrange, outother + otherfile)
    common.logMessage("Done! Extracted", len(files), "files")
