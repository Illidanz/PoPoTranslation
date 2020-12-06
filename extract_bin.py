import codecs
import os
from hacktools import common

knowntypes = ["NPX", "EVX", "TIX", "AN2", "DUM"]


class BINSubfile:
    start = 0
    size = 0
    type = ""

    def __init__(self, start, size, type):
        self.start = start
        self.size = size
        self.type = type


def getBINSubfiles(f, size):
    ret = []
    type = f.readString(3)
    f.seek(0)
    lastpos = 0
    if type in knowntypes:
        while True:
            f.seek(0x800, 1)
            pos = f.tell()
            if pos >= size:
                common.logDebug("Adding last file", lastpos, pos - lastpos, type)
                ret.append(BINSubfile(lastpos, pos - lastpos, type))
                break
            newtype = f.readString(3)
            f.seek(pos)
            if len(newtype) == 3 and common.isAscii(newtype):
                if newtype in knowntypes:
                    ret.append(BINSubfile(lastpos, pos - lastpos, newtype))
                    common.logDebug("Adding file", lastpos, pos - lastpos, newtype)
                    lastpos = pos
                    type = newtype
                else:
                    common.logDebug("Unknown newtype", newtype)
    elif len(type) == 3 and common.isAscii(type):
        common.logMessage("Unknown type", type)
    return ret


def readByte(f):
    global params, strparams
    val = f.readByte()
    params.append(val)
    strparams.append(common.toHex(val).zfill(2))


def readUShort(f):
    global params, strparams
    val = f.readUShort()
    params.append(val)
    strparams.append(common.toHex(val).zfill(4))


def readUInt(f):
    global params, strparams
    val = f.readUInt()
    params.append(val)
    strparams.append(common.toHex(val).zfill(8))


def run():
    global params, strparams
    infolder = "datar/extract/"
    outfile = "datar/bin_output.txt"

    common.logMessage("Extracting BIN...")
    files = common.getFiles(infolder, ".BIN")
    with codecs.open(outfile, "w", "utf-8") as out:
        for file in common.showProgress(files):
            if "NPC1" not in file:
                continue
            common.logDebug("Processing", file)
            size = os.path.getsize(infolder + file)
            with common.Stream(infolder + file, "rb") as f:
                subfiles = getBINSubfiles(f, size)
                for subfile in subfiles:
                    common.logDebug(" Processing subfile", vars(subfile))
                    # Opcodes from "DecodeMainScript"
                    # NPC1.bin arrived 0x82 @0x129
                    if subfile.type == "NPX":
                        f.seek(subfile.start)
                        f.seek(16, 1)
                        subname = f.readString(0x30)
                        out.write("!FILE:" + file.replace(".BIN", "_" + subname) + "\n")
                        ActWk = 6  # ?
                        while True:
                            pos = f.tell()
                            opcode = f.readByte()
                            opname = "?"
                            params = []
                            strparams = []
                            if opcode == 0x80:
                                opname = "?"
                                readUShort(f)
                            elif opcode == 0x81:
                                opname = "DecodeCharScript"
                                readUShort(f)
                                readByte(f)
                                readByte(f)
                                readUShort(f)
                                readUShort(f)
                                readUInt(f)
                                readUInt(f)
                                readUInt(f)
                            elif opcode == 0x82:
                                opname = "LoadMap"
                            elif opcode == 0x84:
                                opname = "?"
                                readUShort(f)
                                readUShort(f)
                            elif opcode == 0x86:
                                opname = "?"
                                readUShort(f)
                            elif opcode == 0x88:
                                opname = "BGM"
                                readByte(f)
                                readUShort(f)
                            elif opcode == 0x8b:
                                opname = "LoadNPC"
                                readUShort(f)
                                readUShort(f)
                            elif opcode == 0x8c:
                                opname = "?"
                                readUShort(f)
                            elif opcode == 0x8d:
                                opname = "MapLoadB"
                                readUShort(f)
                            elif opcode == 0x8f:
                                opname = "?"
                                uVar3 = f.readByte() & 0xff
                                for i in range(uVar3):
                                    if ActWk < 6:
                                        f.readByte()
                                    else:
                                        readUShort(f)
                            elif opcode == 0x9d:
                                opname = "?"
                                readByte(f)
                                readByte(f)
                            elif opcode == 0xa0:
                                opname = "?"
                                readUShort(f)
                                readUShort(f)
                            elif opcode == 0xa3:
                                opname = "MapEffect"
                                for i in range(4):
                                    readUShort(f)
                            elif opcode == 0xfd:
                                opname = "?"
                                readByte(f)
                            elif opcode == 0xfc:
                                opname = "?"
                                readUShort(f)
                            elif opcode == 0xff:
                                opname = "SetEventFnc(10)"
                            elif opcode == 0x01:  # SUB
                                opname = "ChangeChrSeq"
                                readByte(f)
                                readByte(f)
                            elif opcode == 0x02:
                                opname = "?"
                            elif opcode == 0x03:
                                opname = "ChangeChrSeq"
                                readByte(f)
                                readByte(f)
                            elif opcode == 0x04:
                                opname = "SoundEffect"
                                readByte(f)
                                readByte(f)
                                readByte(f)
                                readByte(f)
                            elif opcode == 0x08:
                                opname = "?"
                            elif opcode == 0x10:
                                opname = "CloseWindow"
                            elif opcode == 0x11:
                                opname = "MakeEventWin"
                                readUShort(f)
                            elif opcode == 0x25 or opcode == 0x31:
                                opname = "?"
                                readUShort(f)
                                readByte(f)
                                readUShort(f)
                            elif opcode == 0x30:
                                opname = "LoadEvent"
                                readUShort(f)
                                if ActWk >= 3:
                                    readUShort(f)
                            elif opcode == 0x40:
                                opname = "BgmCmd"
                                readByte(f)
                                readUShort(f)
                                readUShort(f)
                            elif opcode == 0x7d:
                                opname = "?"
                            elif opcode == 0x7c:
                                opname = "EvtChrTug"
                                readUShort(f)
                                readUShort(f)
                                readUShort(f)
                            elif opcode == 0x7e or opcode == 0x7f:
                                opname = "SetChrExtAttr"
                                readUShort(f)
                                readUShort(f)
                            elif opcode == 0x90:
                                opname = "?"
                                readUShort(f)
                                readUShort(f)
                                readUShort(f)
                                readUShort(f)
                                f.readByte()
                                if ActWk >= 5:
                                    readUShort(f)
                            elif opcode == 0x92:
                                opname = "?"
                                readUShort(f)
                                readUShort(f)
                                readByte(f)
                                if ActWk >= 4:
                                    readUShort(f)
                            elif opcode == 0x93:
                                opname = "SetEventFnc(0xc)"
                                readUShort(f)
                                readUShort(f)
                            elif opcode == 0x9a:
                                opname = "EventAttr |= val"
                                readUShort(f)
                            elif opcode == 0x9b:
                                opname = "EventAttr & ~val"
                                readUShort(f)
                            elif opcode == 0xf0:
                                opname = "DelMiniTheater"
                            elif opcode == 0xf7:
                                opname = "?"
                            elif opcode == 0xfe:
                                opname = "?"
                            elif opcode == 0xf8:
                                opname = "Wrong?"
                            else:
                                common.logDebug("  Unknown NPX opcode", common.toHex(opcode))
                                break
                            common.logDebug(" ", common.toHex(opcode).zfill(2), opname, common.toHex(pos), " ".join(strparams))
    common.logMessage("Done! Extracted", len(files), "files")
