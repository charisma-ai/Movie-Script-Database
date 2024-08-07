import json
import os

from tqdm import tqdm
from unidecode import unidecode

from .utilities import create_script_dirs, format_filename, get_pdf_text, get_soup

ALL_URL_1 = "https://thescriptsavant.com/movies.html"
# ALL_URL_2 = "https://thescriptsavant.com/free-movie-screenplays-nz/"
BASE_URL = "https://thescriptsavant.com"
SOURCE = "scriptsavant"
DIR, TEMP_DIR, META_DIR = create_script_dirs(SOURCE)


def get_script_from_url(script_url, file_name):
    text = ""
    try:
        if script_url.endswith(".pdf"):
            text = get_pdf_text(script_url, os.path.join(SOURCE, file_name))
            return text

    except Exception as err:
        print(script_url)
        print(err)
        text = ""

    return text


def get_scriptsavant(metadata_only=True):
    files = [
        os.path.join(DIR, f)
        for f in os.listdir(DIR)
        if os.path.isfile(os.path.join(DIR, f))
        and os.path.getsize(os.path.join(DIR, f)) > 3000
    ]

    metadata = {}
    soup_1 = get_soup(ALL_URL_1)
    # soup_2 = get_soup(ALL_URL_2)

    movielist = soup_1.find_all("a", href=lambda href: href and "/movies/" in href)
    # movielist_2 = soup_2.find_all("div", class_="fusion-text")[0].find_all("a")
    # movielist += movielist_2

    for movie in tqdm(movielist, desc=SOURCE):
        name = movie.text.replace("Script", "").strip()
        file_name = format_filename(name)
        script_url = BASE_URL + movie.get("href")

        metadata[unidecode(name)] = {"file_name": file_name, "script_url": script_url}

        if os.path.join(DIR, file_name + ".txt") in files:
            continue

        if metadata_only:
            continue

        text = get_script_from_url(script_url, file_name)

        if text == "" or file_name == "":
            metadata.pop(name, None)
            continue

        with open(os.path.join(DIR, file_name + ".txt"), "w", errors="ignore") as out:
            out.write(text)

    with open(os.path.join(META_DIR, SOURCE + ".json"), "w") as outfile:
        json.dump(metadata, outfile, indent=4)
