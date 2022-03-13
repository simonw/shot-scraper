import urllib.parse
import re

disallowed_re = re.compile("[^a-zA-Z0-9_-]")


def filename_for_url(url, ext=None, file_exists=None):
    ext = ext or "png"
    if not file_exists:
        file_exists = lambda filename: False
    bits = urllib.parse.urlparse(url)
    filename = (bits.netloc + bits.path).replace(".", "-").replace("/", "-").rstrip("-")
    # Remove any characters outside of the allowed range
    base_filename = disallowed_re.sub("", filename)
    filename = base_filename + "." + ext
    suffix = 0
    while file_exists(filename):
        suffix += 1
        filename = "{}.{}.{}".format(base_filename, suffix, ext)
    return filename
