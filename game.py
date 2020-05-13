import os
from hacktools import common, psx


binranges = [(0, 38390), (832800, 835100)]


def detectEncodedString(f, encoding="shift_jis", startascii=[0x24, 0x25], singlebreak=False):
    ret = ""
    while True:
        b1 = f.readByte()
        if b1 == 0x00:
            break
        elif b1 == 0x0A and singlebreak:
            ret += "|"
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
    return tim, forcepal


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
                            imgranges.append(DATRange(pos + 8, f.tell(), section))
                        elif section == 2 or (section == 3 and extension == ".VIN") or section == 4:
                            # Image
                            sectionpos = f.tell()
                            f.seek(pos + 4 + 4 * section)
                            i = 0
                            while f.tell() < size - 4:
                                timpos = f.tell()
                                forcesize = 0
                                # Fix an image with a wrong size
                                if file.endswith("ETC.VIN") and pos == 487424 and i == 0:
                                    forcesize = 42568
                                tim = readTIM(f, forcesize)
                                if tim is None:
                                    break
                                elif tim:
                                    imgranges.append(DATRange(timpos, f.tell(), section))
                                else:
                                    otherranges.append(DATRange(timpos, f.tell(), section))
                                i += 1
                            f.seek(sectionpos)
                        elif section % 2 == 1:
                            # Script
                            stringrange = DATRange(pos, f.tell(), section)
                            # Check for free space at the end of the section
                            while f.tell() > pos:
                                f.seek(-1, 1)
                                if f.peek(1)[0] != 0x0:
                                    break
                            spacing = f.tell() % 16 if f.tell() % 16 > 0 else 16
                            stringrange.free = f.tell() + spacing
                            f.seek(stringrange.end)
                            stringranges.append(stringrange)
                        else:
                            # Unknown, probably map data?
                            otherranges.append(DATRange(pos, f.tell(), section))
                        break
            else:
                f.seek(0x800, 1)
            pos = f.tell()
    return stringranges, imgranges, otherranges
