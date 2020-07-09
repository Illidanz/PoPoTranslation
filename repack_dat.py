import os
import game
from hacktools import common, psx


def run():
    infolder = "data/extract/"
    outfolder = "data/repack/"
    workfolder = "data/work_IMG/"
    infile = "data/dat_input{}.txt"
    dat = common.openSection(infile)
    if dat is None:
        common.logError("Input file", infile, "not found")
        return
    chartot = transtot = 1

    common.logMessage("Repacking DAT from", infile.format(""), "...")
    files = common.getFiles(infolder, [".DAT", ".VIN"])
    glyphs = game.getFontGlyphs("data/vwf.bin")
    animeglyphs = game.getFontGlyphs("data/vwf.bin", False)
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
                    forcepal = 0 if imgfile.endswith("ETC_007.png") else -1
                    psx.writeTIM(fo, tim, imgfile, False, forcepal)
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
                    # Look for strings (ASCII for the ending credits)
                    if sectionname == "EPISODE5/THEATER1_010":
                        detectfunc = common.detectASCIIString
                    elif sectionname in game.animefiles:
                        detectfunc = game.detectAnimeString
                    else:
                        detectfunc = game.detectEncodedString if stringrange.type != 1 else game.detectVINString
                    extendedstrings = {}
                    freeranges = [[stringrange.free, stringrange.end]]
                    fi.seek(stringrange.start)
                    while fi.tell() < stringrange.end:
                        pos = fi.tell()
                        check = detectfunc(fi)
                        if check != "":
                            if check in section and section[check][0] != "":
                                fo.seek(pos)
                                endpos = fi.tell() - 1
                                newsjis = section[check][0]
                                anime = False
                                maxlen = endpos - pos
                                if newsjis.startswith(">>"):
                                    anime = True
                                    animewidth = 256
                                    newsjis = newsjis[2:]
                                    newsjis = common.wordwrap(newsjis, animeglyphs, animewidth, game.detectTextCode, 8)
                                    maxlen -= 3
                                    # Center each line
                                    animelines = newsjis.split("|")
                                    for j in range(len(animelines)):
                                        animeline = animelines[j]
                                        linelength = 0
                                        for animechar in animeline:
                                            if animechar in animeglyphs:
                                                linelength += animeglyphs[animechar].length
                                            else:
                                                linelength += 8
                                        spacelen = animeglyphs[" "].length
                                        spacing = (animewidth - linelength) // 2 // spacelen
                                        if spacing > 0:
                                            animelines[j] = "<" + common.toHex(0x1e) + "><" + common.toHex(spacing * spacelen) + ">" + animeline
                                    newsjis = "|".join(animelines)
                                    # Split "ee" and "zz", 0x6565 and 0x7a7a are used as control codes
                                    newsjis = newsjis.replace("ee", "e<1E><00>e").replace("zz", "z<1E><00>z")
                                else:
                                    if "%" not in newsjis:
                                        # Only wordwrap if there are no sprintf codes
                                        newsjis = common.wordwrap(newsjis, glyphs, 274, game.detectTextCode, 8)
                                common.logDebug("Writing string at", fo.tell())
                                if anime:
                                    length, x = game.writeAnimeString(fo, newsjis, maxlen)
                                else:
                                    length, x = game.writeEncodedString(fo, newsjis, maxlen)
                                if length < 0:
                                    # String doesn't fit, check if we've already moved it (skip this for anime)
                                    if newsjis in extendedstrings and not anime:
                                        common.logDebug("String doesn't fit", x, "redirected to", extendedstrings[newsjis])
                                        fo.seek(-3, 1)
                                        fo.writeByte(0x1f)
                                        common.logDebug("Redirect 0x1f address:", extendedstrings[newsjis] - fo.tell() + 1)
                                        fo.writeShort(extendedstrings[newsjis] - fo.tell() + 1)
                                    else:
                                        # For non-anime lines, go back 3 characters
                                        if not anime:
                                            x -= 3
                                            # Go back 1 more character if the last one is a $
                                            if newsjis[x - 1] == "$":
                                                x -= 1
                                        stringfit = newsjis[:x]
                                        stringrest = newsjis[x:]
                                        # Find a good freerange
                                        goodrange = -1
                                        for i in range(len(freeranges)):
                                            if freeranges[i][1] - freeranges[i][0] > len(stringrest):
                                                goodrange = i
                                                break
                                        if goodrange >= 0:
                                            rangestart = freeranges[goodrange][0]
                                            rangeend = freeranges[goodrange][1]
                                            # Redirect to free space
                                            common.logDebug("String doesn't fit", x, "redirecting to", rangestart)
                                            fo.seek(pos)
                                            game.writeEncodedString(fo, stringfit)
                                            fo.seek(-1, 1)
                                            fo.writeByte(0x1f)
                                            common.logDebug("Redirect 0x1f address:", rangestart - fo.tell() + 1)
                                            fo.writeShort(rangestart - fo.tell() + 1)
                                            fo.seek(rangestart)
                                            extendedstrings[newsjis] = fo.tell()
                                            length, x = game.writeEncodedString(fo, stringrest, rangeend - rangestart)
                                            if length < 0:
                                                fo.seek(-1, 1)
                                                fo.writeByte(0x0)
                                                common.logError("No room for string", newsjis, stringrest, fo.tell())
                                            else:
                                                if anime:
                                                    # Jump to the end of the original line instead of terminating with 0
                                                    fo.seek(-1, 1)
                                                    fo.writeByte(0x1f)
                                                    fo.writeShort(endpos - fo.tell() + 1)
                                                    freeranges[goodrange][0] += length + 3
                                                else:
                                                    freeranges[goodrange][0] += length + 1
                                        else:
                                            common.logError("No free range for string", newsjis, stringrest, fo.tell())
                                elif anime:
                                    # Jump to the end of the original line instead of terminating with 0
                                    fo.seek(-1, 1)
                                    fo.writeByte(0x1f)
                                    fo.writeShort(endpos - fo.tell() + 1)
                                else:
                                    # Add the rest to the free space
                                    common.logDebug("Adding freerange", fo.tell(), endpos)
                                    freeranges.insert(0, [fo.tell() + 1, endpos])
                            pos = fi.tell() - 1
                        fi.seek(pos + 1)
    dat.close()
    common.logMessage("Done! Translation is at {0:.2f}%".format((100 * transtot) / chartot))
