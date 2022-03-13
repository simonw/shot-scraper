import urllib.parse
import re

disallowed_re = re.compile("[^a-zA-Z0-9_-]")


def file_exists_never(filename):
    return False


def filename_for_url(url, ext=None, file_exists=file_exists_never):
    ext = ext or "png"
    bits = urllib.parse.urlparse(url)
    filename = (bits.netloc + bits.path).replace(".", "-").replace("/", "-").rstrip("-")
    # Remove any characters outside of the allowed range
    base_filename = disallowed_re.sub("", filename).lstrip("-")
    filename = base_filename + "." + ext
    suffix = 0
    while file_exists(filename):
        suffix += 1
        filename = "{}.{}.{}".format(base_filename, suffix, ext)
    return filename


def url_or_file_path(url, file_exists=file_exists_never):
    # If url exists as a file, convert that to file:/
    file_path = file_exists(url)
    if file_path:
        return "file:{}".format(file_path)
    if not (url.startswith("http://") or url.startswith("https://")):
        return "http://{}".format(url)
    return url
