import os
import click
import game
from hacktools import common, psx

version = "0.10.0"
cuein = "data/PoPoLoCrois Monogatari (Japan) (v1.1).cue"
cueout = "data/PoPoLoCrois Monogatari (English).cue"
binin = "data/PoPoLoCrois Monogatari (Japan) (v1.1).bin"
binout = "data/PoPoLoCrois Monogatari (English).bin"
infolder = "data/extract/"
replacefolder = "data/replace/"
exein = "data/extract/SCPS_100.23"
exeout = "data/repack/SCPS_100.23"
outfolder = "data/repack/"


@common.cli.command()
@click.option("--bin", is_flag=True, default=False)
@click.option("--exe", is_flag=True, default=False)
@click.option("--dat", is_flag=True, default=False)
@click.option("--img", is_flag=True, default=False)
@click.option("--mov", is_flag=True, default=False)
def extract(bin, exe, dat, img, mov):
    all = not bin and not exe and not dat and not img and not mov
    if all or bin:
        psx.extractBIN(infolder, outfolder, cuein)
    if all or exe:
        psx.extractEXE(game.binranges, game.detectEXEString, "shift_jis", exein)
    if all or dat:
        import extract_dat
        extract_dat.run()
    if all or img:
        psx.extractTIM("data/extract_IMG/", "data/out_IMG/", readfunc=game.readImage)
    if all or mov:
        import extract_mov
        extract_mov.run()


@common.cli.command()
@click.option("--no-bin", is_flag=True, default=False)
@click.option("--exe", is_flag=True, default=False)
@click.option("--dat", is_flag=True, default=False)
@click.option("--mov", is_flag=True, default=False)
@click.option("--sub", is_flag=True, default=False)
@click.option("--deb", is_flag=True, default=False)
def repack(no_bin, exe, dat, mov, sub, deb):
    all = not exe and not dat and not mov and not sub
    if all or dat:
        import repack_dat
        repack_dat.run()
    if all or mov:
        import repack_mov
        repack_mov.run()
    if all or sub:
        import repack_sub
        repack_sub.run()
    if all or exe or sub or deb:
        # Repack the exe and run armips
        game.generateZoneFile()
        psx.repackEXE(game.binranges, game.freeranges, game.manualptr, game.detectEXEString, game.writeEXEString, "shift_jis", "#", exein, exeout)
        labels = {"DEBUG": 1} if deb else {}
        common.armipsPatch(common.bundledFile("bin_patch.asm"), labels=labels)
    if not no_bin:
        psx.repackBIN(binin, binout, cueout, "data/patch.xdelta")


if __name__ == "__main__":
    click.echo("PoPoTranslation version " + version)
    if not os.path.isdir("data"):
        common.logError("data folder not found.")
        quit()
    common.cli()
