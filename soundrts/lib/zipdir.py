"""
http://stackoverflow.com/questions/3612094/better-way-to-zip-files-in-python-zip-a-whole-directory-with-a-single-command?lq=1
http://stackoverflow.com/questions/10060069/safely-extract-zip-or-tar-using-python
"""

import os
import string
import zipfile

from .log import warning


def zipdir(target_dir, dest_file):
    z = zipfile.ZipFile(dest_file, "w", zipfile.ZIP_DEFLATED)
    rootlen = len(target_dir) + 1
    for base, _, filenames in os.walk(target_dir):
        for n in filenames:
            p = os.path.join(base, n)
            z.write(p, p[rootlen:])


def unzipdir(zip_name, dest, overwrite=False):
    if not overwrite and os.path.exists(dest):
        raise Exception("%s already exists!" % dest)
    zfile = zipfile.ZipFile(zip_name)
    for name in zfile.namelist():
        # This precaution is necessary with Python < 2.7.4 .
        if (
            ".." not in name
            and ":" not in name
            and name[0] in string.ascii_letters + "_"
        ):
            zfile.extract(name, dest)
        else:
            warning("unzipdir: didn't extract %s", name)


if __name__ == "__main__":
    import shutil

    zf = "tmp_zipdirtest.zip"
    if os.path.exists(zf):
        os.remove(zf)
    zipdir("../tests", zf)
    dest = "tmp_tests"
    if os.path.exists(dest):
        shutil.rmtree(dest)
    unzipdir(zf, dest)
    input(f"Check {zf} and {dest}, then press Enter to continue the test.")
    try:
        unzipdir(zf, dest)
    except:
        pass
    else:
        assert False, "An exception should be raised when the destination exists!"
    unzipdir("tmp_zipdirtest.zip", dest, overwrite=True)
    os.remove(zf)
    shutil.rmtree(dest)
