# Imports the map file in ghidra
# Based on https://github.com/NationalSecurityAgency/ghidra/blob/master/Ghidra/Features/Python/ghidra_scripts/ImportSymbolsScript.py
# flake8: noqa

from ghidra.program.model.symbol.SourceType import *
import string

functionManager = currentProgram.getFunctionManager()

f = askFile("Give me a file to open", "Go baby go!")

for line in file(f.absolutePath):
    pieces = line.split()
    if len(pieces) == 6:
        # TODO
        #    Start     Stop   Length      Obj Group            Section name
        # 80010000 8001897F 00008980 80010000 text             .rdata
        continue

    if len(pieces) == 2:
        name = pieces[1]
        address = toAddr(long(pieces[0], 16))

        func = functionManager.getFunctionAt(address)

        if func is not None:
            old_name = func.getName()
            if old_name != name:
                try:
                    func.setName(name, USER_DEFINED)
                except ghidra.util.exception.DuplicateNameException:
                    pass
                print("Renamed function {} to {} at address {}".format(old_name, name, address))
        else:
            try:
                print("Created label {} at address {}".format(name, address))
            except ghidra.util.exception.DuplicateNameException:
                pass
            createLabel(address, name, False)
