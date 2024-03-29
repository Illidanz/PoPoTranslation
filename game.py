import codecs
import os
from hacktools import common, psx

binranges = [
    (0x0,     0x95F6),
    (0xB632C, 0xB6393),
    (0xCB520, 0xCBE1C)
]
freeranges = [
    (0x8064,  0x808A),
    (0x81F0,  0x8206),
    (0x82A8,  0x82F2),
    (0x8518,  0x854A),
    (0x8B58,  0x8D06),
    (0x8D1C,  0x8E00),  # 8fba?
    (0x8FC4,  0x90BE)
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
    # Don't Sell
    0x800160F0: [(0x80071680, "a1")],
    # How many would you like?
    0x80016230: [(0x80073f64, "a1")],
    # Will you equip it?
    0x80016268: [(0x80074460, "a1")],
    # Still want to equip?
    0x800162B8: [(0x80074b58, "a1")],
    # I Want to buy
    0x800162CC: [(0x80075104, "a1")],
    # I want to sell
    0x800162D8: [(0x80075134, "a1")],
    # Never mind
    0x800162E4: [(0x8007514c, "a1")],
    # I thought we were friends
    0x80016360: [(0x80075468, "a1")],
    # it doesn't look like you have anything I want.
    0x8001652C: [(0x80075794, "a1")],
    # What would the King of Devilshh like today?
    0x8001656C: [(0x800758dc, "a1")],
    # Thankshh for your bushhinesshh.
    0x80016A00: [(0x80075cf0, "a1")],
    # Key Items
    0x80017268: [(0x80081b74, "a1")],
    # There's no magic you can use
    0x800172BC: [(0x80083004, "a1")],
    # New recollection.
    0x80017A24: [(0x80093460, "a1"), (0x80094b28, "a1")],
    # Return
    0x80017A74: [(0x8009353c, "a1")],
    # Would you still like to start the game?
    0x80017BE0: [(0x800956f4, "a1")],
    # The treasure chest is empty
    0x80017E44: [(0x80099be4, "a1")],
    # Oh, you're leaving? |Well come back any time. |Especially if you've got something interesting for me.
    0x80016A20: [(0x80075e00, "a1")],
    # Various escape strings
    0x800DADD4: [(0x8003adc8, "a1"), (0x8003ae40, "a1"), (0x8003b5c4, "a1")],
    0x800DADE0: [(0x8003b5a8, "a1")],
    0x800DADE8: [(0x8003be70, "a1")],
    0x800DAE60: [(0x80040c38, "a1")],
    0x800DAE78: [(0x800412d4, "a1")],
    0x800DB2C8: [(0x8007e6a8, "a1"), (0x8007e6c4, "a1"), (0x8007f228, "a1"), (0x8007f34c, "a1"), (0x8007f560, "a1"), (0x800801d4, "a1")],
}
animefiles = [
    "EPISODE1/THEATER1_047", "EPISODE1/THEATER1_049", "EPISODE1/THEATER2_000", "EPISODE1/THEATER2_013",
    "EPISODE2/THEATER3_011", "EPISODE2/THEATER3_012", "EPISODE2/THEATER3_013", "EPISODE2/THEATER3_014", "EPISODE2/THEATER4_001",
    "EPISODE3/THEATER3_005", "EPISODE3/THEATER3_007",
    "EPISODE4/THEATER1_049", "EPISODE4/THEATER2_027"
]


def detectEncodedString(f, encoding="shift_jis", startascii=[0x24, 0x25], singlebreak=False, anime=False):
    ret = ""
    while True:
        b1 = f.readByte()
        if anime:
            animebyte = f.readByte()
            f.seek(-1, 1)
        if b1 == 0x00:
            if anime and len(ret) > 0:
                b2 = f.readByte()
                b3 = f.readByte()
                if b2 == 0 and b3 == 0:
                    ret += "|"
                    continue
                else:
                    f.seek(-2, 1)
                    break
            else:
                break
        elif b1 == 0x0A and singlebreak:
            ret += "|"
        elif b1 == 0x09 and 0x09 in startascii:
            ret += "<09>"
        elif anime and len(ret) > 0 and b1 == 0x65 and animebyte == 0x65:
            f.seek(-1, 1)
            break
        elif anime and len(ret) > 0 and b1 == 0x7a and animebyte == 0x7a:
            ret += "<7A><7A>"
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


def detectAnimeString(f, encoding="shift_jis"):
    return detectEncodedString(f, encoding, anime=True)


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


def writeAnimeString(f, s, maxlen=0, encoding="shift_jis"):
    return writeEncodedString(f, s, maxlen, encoding)


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


def generateZoneFile():
    # Generate the zones.asm file
    with open("data/zones.asm", "w") as f:
        with codecs.open("data/zones.txt", "r", "utf-8") as fin:
            zones = common.getSection(fin, "")
        # Write all the translated zone names
        i = 0
        f.write("ZONE_START:\n")
        for zone in zones:
            f.write("ZONE_" + str(i) + ":\n")
            f.write("  .asciiz \"" + zones[zone][0] + "\"\n")
            i += 1
        i = 0
        f.write("\n.align\n")
        f.write("ZONE_LOOKUP:\n")
        for zone in zones:
            # Sum up all the characters
            sum = 0
            sjis = zone.encode("shift_jis")
            for c in sjis:
                sum += c
            f.write("  .dh 0x" + common.toHex(sum) + "\n")
            f.write("  .dh ZONE_" + str(i) + " - ZONE_START\n")
            i += 1
        f.write("  .dh 0\n.align\n")


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
