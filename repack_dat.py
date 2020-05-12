import codecs
import os
import game
from hacktools import common


def run():
    infolder = "data/extract/"
    outfolder = "data/repack/"
    infile = "data/dat_input.txt"
    if not os.path.isfile(infile):
        common.logError("Input file", infile, "not found")
        return
    chartot = transtot = 0

    common.logMessage("Repacking DAT from", infile, "...")
    with codecs.open(infile, "r", "utf-8") as dat:
        files = common.getFiles(infolder, ".DAT")
        for file in common.showProgress(files):
            common.copyFile(infolder + file, outfolder + file)
            common.logDebug("Processing", file, "...")
            stringranges, imgranges, mapranges = game.getDatRanges(infolder + file, ".DAT")
            with common.Stream(infolder + file, "r+b") as fi:
                with common.Stream(outfolder + file, "r+b") as fo:
                    # Loop all script files
                    for i in range(len(stringranges)):
                        # Get section data
                        stringrange = stringranges[i]
                        sectionname = file.replace(".DAT", "_" + str(i).zfill(3))
                        section = common.getSection(dat, sectionname)
                        chartot, transtot = common.getSectionPercentage(section, chartot, transtot)
                        # Skip if empty
                        if len(section) == 0:
                            continue
                        allempty = True
                        for string in section:
                            if section[string][0] != "":
                                allempty = False
                                break
                        if allempty:
                            continue
                        # Look for strings
                        fi.seek(stringrange[0])
                        while fi.tell() < stringrange[1]:
                            pos = fi.tell()
                            check = game.detectEncodedString(fi)
                            if check != "":
                                if check in section and section[check][0] != "":
                                    fo.seek(pos)
                                    endpos = fi.tell() - 1
                                    newsjis = section[check][0]
                                    # Only wordwrap if there are no sprintf codes
                                    if "%" not in newsjis:
                                        newsjis = common.wordwrap(newsjis, {}, 290, game.detectTextCode, 9)
                                    game.writeEncodedString(fo, newsjis, endpos - pos + 1)
                                    fo.seek(-1, 1)
                                    if fo.readByte() != 0:
                                        fo.writeZero(1)
                                pos = fi.tell() - 1
                            fi.seek(pos + 1)
    common.logMessage("Done! Translation is at {0:.2f}%".format((100 * transtot) / chartot))
