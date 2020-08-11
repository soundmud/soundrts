#! .venv\Scripts\python.exe
import os
import shutil
from os.path import join

from docutils import core

import rules2doc

SRC = "doc_src/src"

def build(dest="."):
    DEST = join(dest, "doc")
    try:
        os.makedirs(DEST)
    except OSError:
        pass

    for lang in ("es", "it"):
        p = join(SRC, lang, "htm")
        dp = join(DEST, lang)
        try:
            os.mkdir(dp)
        except OSError:
            pass
        for n in os.listdir(p):
            shutil.copyfile(join(p, n), join(dp, n))

    for lang in ("en", "pt-BR"):
        p = join(SRC, lang)
        dp = join(DEST, lang)
        open(join(p, "stats.inc"), "w").write(rules2doc.stats)
        try:
            os.mkdir(dp)
        except OSError:
            pass
        for n in os.listdir(p):
            if n.endswith(".rst"):
                core.publish_file(source_path=join(p, n), writer_name="html",
                                  destination_path=join(dp, n[:-3] + "htm"))

    shutil.copyfile(join(DEST, "en/units.htm"), join(DEST, "it/units.htm"))
    for n in ("mapmaking", "modding", "aimaking"):
        shutil.copyfile(join(DEST, "en/%s.htm" % n),
                        join(DEST, "pt-BR/%s.htm" % n))


if __name__ == "__main__":
    build()
