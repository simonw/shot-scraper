import urllib.parse
import re
import os.path

disallowed_re = re.compile("[^a-zA-Z0-9_-]")

# Map content-type to file extension
CONTENT_TYPE_EXTENSIONS = {
    "text/html": "html",
    "text/css": "css",
    "application/javascript": "js",
    "text/javascript": "js",
    "application/json": "json",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/svg+xml": "svg",
    "application/pdf": "pdf",
    "text/plain": "txt",
    "application/xml": "xml",
    "text/xml": "xml",
    "font/woff2": "woff2",
    "font/woff": "woff",
    "application/font-woff": "woff",
}

# Map file extension to expected content-type prefix
EXTENSION_CONTENT_TYPES = {
    "html": "text/html",
    "htm": "text/html",
    "css": "text/css",
    "js": "application/javascript",
    "json": "application/json",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    "svg": "image/svg+xml",
    "pdf": "application/pdf",
    "txt": "text/plain",
    "xml": "application/xml",
    "woff2": "font/woff2",
    "woff": "font/woff",
}


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
        filename = f"{base_filename}.{suffix}.{ext}"
    return filename


def url_or_file_path(url, file_exists=file_exists_never):
    # If url exists as a file, convert that to file:/
    file_path = file_exists(url)
    if file_path:
        return f"file:{file_path}"
    if not (url.startswith("http://") or url.startswith("https://")):
        return f"http://{url}"
    return url


def load_github_script(github_path: str) -> str:
    """
    Load JavaScript script from GitHub

    Format: username/repo/path/to/file.js
      or username/file.js which means username/shot-scraper-scripts/file.js
    """
    if not github_path.endswith(".js"):
        github_path += ".js"
    parts = github_path.split("/")

    if len(parts) == 2:
        # Short form: username/file.js
        username, file_name = parts
        parts = [username, "shot-scraper-scripts", file_name]

    if len(parts) < 3:
        raise ValueError(
            "GitHub path format should be 'username/repo/path/to/file.js' or 'username/file.js'"
        )

    username = parts[0]
    repo = parts[1]
    file_path = "/".join(parts[2:])

    # Fetch from GitHub
    import urllib.request

    url = f"https://raw.githubusercontent.com/{username}/{repo}/main/{file_path}"
    try:
        with urllib.request.urlopen(url) as response:
            if response.status == 200:
                return response.read().decode("utf-8")
            else:
                raise ValueError(
                    f"Failed to load content from GitHub: HTTP {response.status}\n"
                    f"URL: {url}"
                )
    except urllib.error.URLError as e:
        raise ValueError(f"Error fetching from GitHub: {e}")


def extension_for_content_type(content_type):
    """
    Return the file extension for a given content-type.

    Returns None if the content-type is unknown or empty.
    """
    if not content_type:
        return None
    # Strip charset and other parameters
    mime_type = content_type.split(";")[0].strip().lower()
    return CONTENT_TYPE_EXTENSIONS.get(mime_type)


def filename_for_har_entry(url, content_type, file_exists=file_exists_never):
    """
    Derive a filename for a HAR entry based on its URL and content-type.

    Uses the URL to generate a base filename, then determines the extension:
    - If the URL has an extension that matches the content-type, use it
    - If the URL has no extension, or the extension doesn't match, use content-type
    - If neither URL nor content-type provide an extension, use .bin
    """
    bits = urllib.parse.urlparse(url)
    url_path = bits.path

    # Try to get extension from URL path
    path_base, url_ext_with_dot = os.path.splitext(url_path)
    url_ext = url_ext_with_dot.lstrip(".").lower() if url_ext_with_dot else None

    # Get extension from content-type
    ct_ext = extension_for_content_type(content_type)

    # Determine if URL extension matches content-type
    url_ext_matches_ct = False
    if url_ext and ct_ext:
        expected_ct = EXTENSION_CONTENT_TYPES.get(url_ext, "").lower()
        actual_ct = content_type.split(";")[0].strip().lower() if content_type else ""
        if expected_ct and expected_ct == actual_ct:
            url_ext_matches_ct = True
        elif url_ext in ("jpg", "jpeg") and ct_ext in ("jpg", "jpeg"):
            url_ext_matches_ct = True

    # Get base filename from URL (netloc + path, excluding query)
    # Only strip extension from path if it matches content-type
    if url_ext and url_ext_matches_ct:
        path_for_base = path_base
    else:
        path_for_base = url_path
    base = (bits.netloc + path_for_base).replace(".", "-").replace("/", "-").rstrip("-")
    base = disallowed_re.sub("", base).lstrip("-")

    # Determine final extension
    if url_ext_matches_ct:
        ext = url_ext
    elif ct_ext:
        ext = ct_ext
    elif url_ext:
        ext = url_ext
    else:
        ext = "bin"

    filename = f"{base}.{ext}"
    suffix = 0
    while file_exists(filename):
        suffix += 1
        filename = f"{base}.{suffix}.{ext}"
    return filename
