import codecs
import os
import ass
import game
from hacktools import common

subfiles = [
    ("NA_BUR01.XA[3].ass", 0x21c3)
]


def run():
    infolder = "data/work_SUB/"
    outfile = "data/softsubs.asm"

    common.logMessage("Generating SUB...")
    glyphs = game.getFontGlyphs("data/vwf.bin")
    subi = 0
    with codecs.open(outfile, "w", "utf-8") as sub:
        subdata = []
        for subfile in common.showProgress(subfiles):
            if not os.path.isfile(infolder + subfile[0]):
                continue
            common.logDebug("Processing", subfile[0])
            subdata.append(subfile[1])
            with codecs.open(infolder + subfile[0], "r", "utf-8-sig") as f:
                doc = ass.parse(f)
            sub.write("SUB_DATA_" + str(subi) + ":\n")
            lines = []
            for event in doc.events:
                line = event.text.strip()
                line = common.wordwrap(line, glyphs, 274, game.detectTextCode, 8)
                linestart = common.deltaToFrame(event.start, 125)
                lineend = common.deltaToFrame(event.end, 125)
                lines.append((line, linestart, lineend))
            for i in range(len(lines)):
                line = lines[i]
                sub.write("  .dh {}\n".format(str(line[1])))
                sub.write("  .ascii \"{}\"\n".format(line[0].replace("|", "\" :: .db 0xa :: .ascii \"")))
                sub.write("  .db 0x0\n\n")
                if i == len(lines) - 1 or line[2] != lines[i+1][1]:
                    sub.write("  .dh {}\n".format(str(line[2])))
                    sub.write("  .db 0x0\n\n")
            subi += 1
            sub.write("  .dh 0\n\n")
        sub.write(".align\n\n")
        sub.write("SUB_DATA:\n")
        for i in range(len(subdata)):
            sub.write("  .dw 0x{}\n".format(common.toHex(subdata[i])))
            sub.write("  .dw SUB_DATA_{0}\n".format(str(i)))
        sub.write("  .dw 0")
    common.logMessage("Done!")
