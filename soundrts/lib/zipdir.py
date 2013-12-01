"""
http://stackoverflow.com/questions/3612094/better-way-to-zip-files-in-python-zip-a-whole-directory-with-a-single-command?lq=1
"""

import os
import zipfile


def zipdir(target_dir, dest_file):
    zip = zipfile.ZipFile(dest_file, 'w', zipfile.ZIP_DEFLATED)
    rootlen = len(target_dir) + 1
    for base, dirs, files in os.walk(target_dir):
        for file in files:
            fn = os.path.join(base, file)
            zip.write(fn, fn[rootlen:])

def unzipdir(zip_name, dest, overwrite=False):
    if not overwrite and os.path.exists(dest):
        raise Exception("%s already exists!" % dest)
    zfile = zipfile.ZipFile(zip_name)
    for name in zfile.namelist():
        abs_name = os.path.join(dest, name)
        (dirname, filename) = os.path.split(abs_name)
        if not os.path.exists(dirname):
            os.mkdir(dirname)
        open(abs_name, "wb").write(zfile.read(name))


if __name__ == "__main__":
    import shutil
    zf = "tmp_zipdirtest.zip"
    if os.path.exists(zf):
        os.remove(zf)
    zipdir("tests", zf)
    dest = "tmp_tests"
    if os.path.exists(dest):
        shutil.rmtree(dest)
    unzipdir(zf, dest)
    try:
        unzipdir(zf, dest)
    except:
        pass
    else:
        assert False, "An exception should be raised when the destination exists!"
    unzipdir("tmp_zipdirtest.zip", dest, overwrite=True)
    os.remove(zf)
    shutil.rmtree(dest)
