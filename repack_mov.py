import codecs
import os
import ass
import game
from PIL import Image
from hacktools import common


def run():
    infolder = "data/extract/M2F2/"
    outfolder = "data/repack/M2F2/"
    extractfolder = "data/extract_MOV/"
    repackfolder = "data/repack_MOV/"
    xmlfile = "data/replace.xml"
    fontfile = "data/subfont.png"

    common.logMessage("Repacking MOV...")
    if not os.path.isfile("jpsxdec\\jpsxdec.jar"):
        common.logError("jpsxdec not found")
        return
    common.makeFolder(repackfolder)
    files = common.getFiles(infolder, ".MOV")

    for file in common.showProgress(files):
        common.logDebug("Processing", file)
        glyphs = game.getFontGlyphs("data/vwf.bin")
        # Copy the file and setup folders
        extractmov = extractfolder + file.replace(".MOV", "") + "/"
        repackmov = repackfolder + file.replace(".MOV", "") + "/"
        common.makeFolder(repackmov)
        common.copyFile(infolder + file, outfolder + file)
        # Read the subtitles
        subin = "data/work_SUB/" + file.replace(".MOV", ".ass")
        if not os.path.isfile(subin):
            continue
        with codecs.open(subin, "r", "utf-8-sig") as f:
            doc = ass.parse(f)
        # Setup the font
        fontimg = Image.open(fontfile).convert("RGBA")
        # Create the jpsxdec xml file
        with codecs.open(xmlfile, "w") as xml:
            xml.write("<?xml version=\"1.0\"?>\n")
            xml.write("<str-replace version=\"0.2\">\n")
            for event in doc.events:
                line = event.text.strip()
                linestart = common.deltaToFrame(event.start, 15)
                lineend = common.deltaToFrame(event.end, 15)
                # Draw the text and crop it
                txt = Image.new("RGBA", (320, 240), (0, 0, 0, 0))
                x = 0
                for char in line:
                    i = ord(char) - 0x21
                    if i >= 0:
                        glyph = fontimg.crop((i * 8, 0, i * 8 + 8, 15))
                        txt.paste(glyph, (x, 0), glyph)
                    if char in glyphs:
                        x += glyphs[char].length
                    else:
                        x += 8
                txt = txt.crop(txt.getbbox())
                txtpos = ((320 - txt.width) // 2, 224 - 15 - 5)
                # Edit all frames where the line appears
                for i in range(linestart, lineend):
                    framename = file + "[0][" + str(i).zfill(4) + "].png"
                    frame = Image.open(extractmov + framename).convert("RGBA")
                    frame.paste(txt, txtpos, txt)
                    frame.save(repackmov + framename)
                    xml.write("    <replace frame=\"{i}\">{frame}</replace>\n".format(i=str(i), frame=repackmov + framename))
            xml.write("</str-replace>\n")
        common.execute("java -jar jpsxdec\\jpsxdec.jar -f \"{mov}\" -i 0 -replaceframes \"{xml}\"".format(mov=outfolder + file, xml=xmlfile), False)
        os.remove(xmlfile)
    # Clear log files
    for log in common.getFiles(os.getcwd(), ".log"):
        if log != "/tool.log":
            os.remove(log[1:])
    common.logMessage("Done!")
