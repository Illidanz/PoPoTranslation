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
                        extendedstrings = {}
                        fi.seek(stringrange.start)
                        while fi.tell() < stringrange.end:
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
                                    common.logDebug("Writing string at", fo.tell())
                                    length, x = game.writeEncodedString(fo, newsjis, endpos - pos)
                                    if length < 0:
                                        # String doesn't fit, check if we've already moved it
                                        if newsjis in extendedstrings:
                                            common.logDebug("String doesn't fit", x, "redirected to", extendedstrings[newsjis])
                                            fo.seek(-3, 1)
                                            fo.writeByte(0x1f)
                                            fo.writeUShort(extendedstrings[newsjis] - fo.tell() + 1)
                                        else:
                                            # Redirect to free space
                                            # Go back 3 characters and write the string again
                                            common.logDebug("String doesn't fit", x, "redirecting to", stringrange.free)
                                            x -= 3
                                            stringfit = newsjis[:x]
                                            stringrest = newsjis[x:]
                                            fo.seek(pos)
                                            game.writeEncodedString(fo, stringfit)
                                            fo.seek(-1, 1)
                                            fo.writeByte(0x1f)
                                            fo.writeUShort(stringrange.free - fo.tell() + 1)
                                            fo.seek(stringrange.free)
                                            extendedstrings[newsjis] = fo.tell()
                                            length, x = game.writeEncodedString(fo, stringrest, stringrange.end - stringrange.free)
                                            if length < 0:
                                                fo.seek(-1, 1)
                                                fo.writeByte(0x0)
                                                common.logError("No room for string", newsjis, fo.tell())
                                            else:
                                                stringrange.free += length + 1
                                pos = fi.tell() - 1
                            fi.seek(pos + 1)
    common.logMessage("Done! Translation is at {0:.2f}%".format((100 * transtot) / chartot))
