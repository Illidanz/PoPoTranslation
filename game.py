import os
from hacktools import common, psx

binranges = [
    (0x0,     0x95F6),
    (0xCB520, 0xCBE1C)
]
freeranges = [
    (0x7C70,  0x7E8E),
    (0x8064,  0x808A),
    (0x81F0,  0x8206),
    (0x82A8,  0x82F2),
    (0x8518,  0x854A),
    (0x855C,  0x85EA)
]
manualptr = {
    # Formation 0%d
    0x80017434: [(0x8008a0f8, "a1"), (0x8008a338, "a1")],
    # You defeated the monsters!
    0x80010BF8: [(0x8003d534, "a1")],
    # Pietro and his friends have fallen.
    0x80010C24: [(0x8003d704, "a1")],
    # Pietro and his friends ran away.
    0x80010C54: [(0x8003d7e0, "a1")],
    # Everyone ran away!
    0x80010C70: [(0x8003d8a8, "a1")],
    # Gained magic experience.
    0x80011080: [(0x80045194, "a1")],
    # The enemy caught up!
    0x80010C84: [(0x8003d920, "a1")],
    # They are now level %d.
    0x80010FDC: [(0x80044aa0, "a1")],
    # They learned %s.
    0x80011034: [(0x80044b2c, "a1"), (0x80044b58, "a1")],
    # %s gained %d
    0x80011048: [(0x80045120, "a1")],
    # %s and his friends gained %d
    0x80011054: [(0x80045110, "a1"), (0x80045180, "a1")],
    # Shop gold
    0x800160E4: [(0x80071644, "a1")],
    0x800161B0: [(0x8007368c, "a1")],
}


def detectEncodedString(f, encoding="shift_jis", startascii=[0x24, 0x25], singlebreak=False):
    ret = ""
    while True:
        b1 = f.readByte()
        if b1 == 0x00:
            break
        elif b1 == 0x0A and singlebreak:
            ret += "|"
        elif b1 == 0x09 and 0x09 in startascii:
            ret += "<09>"
        elif b1 >= 0x20 and b1 <= 0x7e and (len(ret) > 0 or b1 in startascii):
            ret += chr(b1)
        else:
            b2 = f.readByte()
            if b1 == 0x0A and b2 == 0x0B:
                ret += "|"
            elif common.checkShiftJIS(b1, b2):
                f.seek(-2, 1)
                try:
                    ret += f.read(2).decode(encoding).replace("〜", "～")
                except UnicodeDecodeError:
                    return ""
            else:
                return ""
    if len(ret) == 1:
        return ""
    return ret


def detectVINString(f, encoding="shift_jis"):
    return detectEncodedString(f, encoding, [0x24, 0x25, 0x09])


def detectEXEString(f, encoding="shift_jis"):
    return detectEncodedString(f, encoding, singlebreak=True)


def writeEncodedString(f, s, maxlen=0, encoding="shift_jis", singlebreak=False):
    i = 0
    x = 0
    s = s.replace("～", "〜")
    while x < len(s):
        c = s[x]
        if c == "U" and x < len(s) - 4 and s[x:x+4] == "UNK(":
            if maxlen > 0 and i+2 > maxlen:
                return -1, x
            code = s[x+4] + s[x+5]
            f.write(bytes.fromhex(code))
            code = s[x+6] + s[x+7]
            f.write(bytes.fromhex(code))
            x += 8
            i += 2
        elif c == "<" and x < len(s) - 3 and s[x+3] == ">":
            if maxlen > 0 and i+1 > maxlen:
                return -1, x
            code = s[x+1] + s[x+2]
            f.write(bytes.fromhex(code))
            x += 3
            i += 1
        elif c == "|":
            if maxlen > 0 and i+1 > maxlen:
                return -1, x
            f.writeByte(0x0A)
            i += 1
        elif ord(c) < 128:
            if maxlen > 0 and i+1 > maxlen:
                return -1, x
            f.writeByte(ord(c))
            i += 1
        else:
            if maxlen > 0 and i+2 > maxlen:
                return -1, x
            f.write(c.encode(encoding))
            i += 2
        x += 1
    f.writeByte(0x00)
    return i, x


def writeEXEString(f, s, maxlen=0, encoding="shift_jis"):
    length, x = writeEncodedString(f, s, maxlen, encoding, singlebreak=True)
    return length


def detectTextCode(s, i=0):
    if s[i] == "$":
        return 2
    if s[i] == "@":
        return 1
    if s[i] == "<":
        return 4
    return 0


def extractFile(f, range, filename):
    f.seek(range[0])
    common.makeFolders(os.path.dirname(filename))
    with common.Stream(filename, "wb") as fout:
        fout.write(f.read(range[1] - range[0]))


def isSection(f):
    unk1 = f.readUInt()
    unk2 = f.readUShort()
    unk3 = f.readUShort()
    f.seek(-8, 1)
    if unk1 > 0 and unk1 <= 0xff and unk2 != 0 and unk3 >= 0x8000 and unk3 <= 0x8020:
        # common.logDebug("Section>>", common.toHex(f.tell()), common.toHex(unk1), common.toHex(unk2), common.toHex(unk3))
        return unk1
    return 0


def readImage(file):
    with common.Stream(file, "rb") as f:
        tim = psx.readTIM(f)
    forcepal = -1
    if file.endswith("ETC_007.tim"):
        forcepal = 0
    return tim, False, forcepal


def readTIM(f, forcesize):
    pos = f.tell()
    tim = psx.readTIM(f, forcesize)
    if tim is not None:
        return True
    f.seek(pos)
    header = f.readUInt()
    if header != 0x13:
        return None
    f.seek(4, 1)
    size = f.readUInt()
    f.seek(size - 4, 1)
    return False


def getFontGlyphs(file, first=True):
    glyphs = {}
    fontglyphs = "!\"%&'()**,-./0123456789:;<=>?ABC EFGHIJKLMNOPQRSTUVWXYZ[];abcdefghijklmnopqrstuvwxyz_______D~___"
    with common.Stream(file, "rb") as f:
        if not first:
            f.seek(0x60)
        for i in range(len(fontglyphs)):
            width = f.readByte()
            glyphs[fontglyphs[i]] = common.FontGlyph(0, width, width)
    return glyphs


def getScriptFree(f, pos):
    # Check for free space at the end of the section
    while f.tell() > pos:
        f.seek(-1, 1)
        if f.peek(1)[0] != 0x0:
            break
    padding = f.tell() % 16 if f.tell() % 16 > 0 else 16
    return f.tell() + padding


def addStringRange(f, start, end, section, pos):
    stringrange = DATRange(start, end, section)
    stringrange.free = getScriptFree(f, pos)
    f.seek(stringrange.end)
    return stringrange


class DATRange:
    start = 0
    end = 0
    type = 0
    free = 0

    def __init__(self, start, end, type):
        self.start = start
        self.end = end
        self.type = type


def getDatRanges(file, extension):
    size = os.path.getsize(file)
    stringranges = []
    imgranges = []
    otherranges = []
    with common.Stream(file, "rb") as f:
        pos = 0
        while pos < size - 8:
            section = isSection(f)
            if section != 0:
                while True:
                    f.seek(0x800, 1)
                    if f.tell() == size or isSection(f) != 0:
                        if section == 1:
                            # Image
                            imgrange = DATRange(pos + 8, f.tell(), section)
                            # Fix image with wrong size
                            if file.endswith("ETC.VIN") and pos == 1732608:
                                imgrange.end -= 0x3600
                                # Item descriptions
                                stringranges.append(addStringRange(f, imgrange.end, imgrange.end + 0x3600, section, pos))
                            imgranges.append(imgrange)
                        elif section == 2 or (section == 3 and extension == ".VIN") or section == 4:
                            # Image
                            sectionpos = f.tell()
                            f.seek(pos + 4 + 4 * section)
                            i = 0
                            while f.tell() < size - 4:
                                timpos = f.tell()
                                forcesize = 0
                                # Fix images with wrong size
                                if file.endswith("ETC.VIN"):
                                    if pos == 487424 and i == 0:
                                        forcesize = 42568
                                    elif pos == 1902592 and i == 0:
                                        forcesize = 89888
                                    elif pos == 1902592 and i == 1:
                                        forcesize = 154614
                                tim = readTIM(f, forcesize)
                                if tim is None:
                                    if file.endswith("ETC.VIN") and pos == 1902592 and i == 3:
                                        # Monster/Skill descriptions
                                        stringranges.append(addStringRange(f, timpos, timpos + 8128, section, timpos))
                                        stringranges.append(addStringRange(f, timpos + 8128, sectionpos, section, timpos + 8128))
                                    break
                                elif tim:
                                    imgranges.append(DATRange(timpos, f.tell(), section))
                                else:
                                    otherranges.append(DATRange(timpos, sectionpos, section))
                                i += 1
                            f.seek(sectionpos)
                        elif section % 2 == 1:
                            # Script
                            stringranges.append(addStringRange(f, pos, f.tell(), section, pos))
                        else:
                            # Unknown, probably map data?
                            otherranges.append(DATRange(pos, f.tell(), section))
                        break
            else:
                f.seek(0x800, 1)
            pos = f.tell()
    return stringranges, imgranges, otherranges
