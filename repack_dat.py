import codecs
import os
import game
from hacktools import common, psx


def run():
    infolder = "data/extract/"
    outfolder = "data/repack/"
    workfolder = "data/work_IMG/"
    infile = "data/dat_input.txt"
    if not os.path.isfile(infile):
        common.logError("Input file", infile, "not found")
        return
    chartot = transtot = 1

    common.logMessage("Repacking DAT from", infile, "...")
    with codecs.open(infile, "r", "utf-8") as dat:
        files = common.getFiles(infolder, [".DAT", ".VIN"])
        glyphs = game.getFontGlyphs("data/vwf.bin")
        for file in common.showProgress(files):
            extension = os.path.splitext(file)[1]
            common.copyFile(infolder + file, outfolder + file)
            common.logDebug("Processing", file, "...")
            stringranges, imgranges, otherranges = game.getDatRanges(infolder + file, extension)
            with common.Stream(infolder + file, "r+b") as fi:
                with common.Stream(outfolder + file, "r+b") as fo:
                    # Loop all images
                    for i in range(len(imgranges)):
                        imgrange = imgranges[i]
                        imgfile = workfolder + file.replace(extension, "_" + str(i).zfill(3)) + ".png"
                        # Skip if not edited
                        if not os.path.isfile(imgfile):
                            continue
                        common.logDebug("Writing image", imgfile)
                        fi.seek(imgrange.start)
                        fo.seek(imgrange.start)
                        tim = psx.readTIM(fi)
                        psx.writeTIM(fo, tim, imgfile, 0 if imgfile.endswith("ETC_007.png") else -1)
                    # Loop all script files
                    for i in range(len(stringranges)):
                        # Get section data
                        stringrange = stringranges[i]
                        sectionname = file.replace(extension, "_" + str(i).zfill(3))
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
                        detectfunc = game.detectEncodedString if stringrange.type != 1 else game.detectVINString
                        extendedstrings = {}
                        fi.seek(stringrange.start)
                        while fi.tell() < stringrange.end:
                            pos = fi.tell()
                            check = detectfunc(fi)
                            if check != "":
                                if check in section and section[check][0] != "":
                                    fo.seek(pos)
                                    endpos = fi.tell() - 1
                                    newsjis = section[check][0]
                                    # Only wordwrap if there are no sprintf codes
                                    if "%" not in newsjis:
                                        newsjis = common.wordwrap(newsjis, glyphs, 276, game.detectTextCode, 8)
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
