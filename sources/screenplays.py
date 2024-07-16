import json
import os
import urllib

from tqdm import tqdm

from .utilities import create_script_dirs, format_filename, get_soup

ALL_URL = "https://www.screenplays-online.de/"
BASE_URL = "https://www.screenplays-online.de/"
SOURCE = "screenplays"
DIR, TEMP_DIR, META_DIR = create_script_dirs(SOURCE)


def get_script_from_url(script_url, file_name):
    script_soup = get_soup(script_url)
    if script_soup is None:
        return ""

    if not script_soup.pre:
        return ""
    return script_soup.pre.get_text()


def get_screenplays(metadata_only=True):
    files = [
        os.path.join(DIR, f)
        for f in os.listdir(DIR)
        if os.path.isfile(os.path.join(DIR, f))
        and os.path.getsize(os.path.join(DIR, f)) > 3000
    ]

    metadata = {}
    soup = get_soup(ALL_URL)
    mlist = soup.find_all("table", class_="screenplay-listing")[0].find_all("a")
    movielist = [x for x in mlist if x.get("href").startswith("screenplay")]

    for movie in tqdm(movielist, desc=SOURCE):
        name = movie.text
        file_name = format_filename(name)
        script_url = BASE_URL + urllib.parse.quote(movie.get("href"))
        # if script_url.startswith("screenplay"):

        metadata[name] = {"file_name": file_name, "script_url": script_url}

        if os.path.join(DIR, file_name + ".txt") in files:
            continue

        if metadata_only:
            continue

        text = get_script_from_url(script_url, file_name)

        if text == "" or name == "":
            metadata.pop(name, None)
            continue

        with open(os.path.join(DIR, file_name + ".txt"), "w", errors="ignore") as out:
            out.write(text)

    with open(os.path.join(META_DIR, SOURCE + ".json"), "w") as outfile:
        json.dump(metadata, outfile, indent=4)
