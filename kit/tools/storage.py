"""Keep the heavy, long-lived workspace data on Google Drive and only code + scratch on the Mac.
    python tools/storage.py status                 where each folder lives and how big it is
    python tools/storage.py to-drive [DRIVE_DIR]   move videos/ sfxlib/ research/ assets/ music/ _backups/ to Drive, leave symlinks
Local on purpose: rbx/ tools/ docs/ sfx/ config.json .env (API key: never uploaded) .venv/ and the scratch dir (config tmp_dir)
where render frames/blend/caps live and are deleted after finish.py (auto_clean_frames).
DRIVE_DIR default: ~/Library/CloudStorage/GoogleDrive-*/My Drive/RobloxStories (Google Drive for desktop must be running)."""
import glob, os, shutil, subprocess, sys

STUDIO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOVE = ["videos", "sfxlib", "research", "assets", "music", "_backups"]


def drive_default():
    g = glob.glob(os.path.expanduser("~/Library/CloudStorage/GoogleDrive-*/My Drive"))
    return os.path.join(g[0], "RobloxStories") if g else None


def size(p):
    t = 0
    for r, _, fs in os.walk(os.path.realpath(p)):
        for f in fs:
            try:
                t += os.path.getsize(os.path.join(r, f))
            except OSError:
                pass
    return t


def status():
    for n in MOVE:
        p = os.path.join(STUDIO, n)
        if os.path.islink(p):
            print(f"{n:10s} -> {os.path.realpath(p)}  ({size(p) / 1e6:.0f} MB, on Drive)")
        elif os.path.exists(p):
            print(f"{n:10s} local ({size(p) / 1e6:.0f} MB)")


def to_drive(dest):
    os.makedirs(dest, exist_ok=True)
    for n in MOVE:
        src, dst = os.path.join(STUDIO, n), os.path.join(dest, n)
        if os.path.islink(src) or not os.path.exists(src):
            continue
        subprocess.run(["rsync", "-a", "--exclude", "frames", "--exclude", "blend", "--exclude", "caps", src + "/", dst + "/"], check=True)
        a = sum(len(fs) for _, _, fs in os.walk(src) if "/frames" not in _ and "/blend" not in _)
        b = sum(len(fs) for _, _, fs in os.walk(dst))
        if b < a:
            sys.exit(f"copy of {n} incomplete ({b} of {a} files): left everything in place")
        shutil.rmtree(src)
        os.symlink(dst, src)
        print(f"moved {n} -> {dst}")


if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]
    if a[0] == "status":
        status()
    elif a[0] == "to-drive":
        d = a[1] if len(a) > 1 else drive_default()
        if not d:
            sys.exit("Google Drive for desktop folder not found")
        to_drive(d)
        status()
    else:
        print(__doc__)
