import json
import os
import re
import urllib

from tqdm import tqdm

from .utilities import create_script_dirs, format_filename, get_pdf_text, get_soup


def get_scriptslug(metadata_only=True):
    ALL_URL_1 = "https://www.scriptslug.com/scripts/medium/film/?pg="
    # ALL_URL_2 = "https://www.scriptslug.com/scripts/medium/series/?pg="
    BASE_URL = "https://assets.scriptslug.com/live/pdf/scripts/"
    SOURCE = "scriptslug"
    DIR, TEMP_DIR, META_DIR = create_script_dirs(SOURCE)

    def get_script_from_url(script_url, file_name):
        text = ""

        try:
            text = get_pdf_text(script_url, os.path.join(SOURCE, file_name))
            return text

        except Exception as err:
            print(script_url)
            print(err)
            text = ""

        return text

    def get_script_url(movie):
        script_url = movie["href"].split("/")[-1]

        name = movie["aria-label"].replace("Script", "")
        name = re.sub(r"\(.*\)", "", name).strip()

        # name = (
        #     movie.find_all(class_="script__title")[0]
        #     .find(text=True, recursive=False)
        #     .strip()
        # )
        file_name = re.sub(r"\([^)]*\)", "", format_filename(name))

        return script_url, file_name, name

    files = [
        os.path.join(DIR, f)
        for f in os.listdir(DIR)
        if os.path.isfile(os.path.join(DIR, f))
        and os.path.getsize(os.path.join(DIR, f)) > 3000
    ]

    metadata = {}
    TOTAL_PAGES = 60

    print(f"Fetching scripts from {SOURCE}")
    movielist = set()
    for pg in range(10, TOTAL_PAGES, 10):
        soup = get_soup(ALL_URL_1 + str(pg))
        linklist = soup.find_all("a", href=lambda href: href and "/script/" in href)
        movielist.update(linklist)

    for movie in tqdm(movielist, desc=SOURCE):
        script_url, file_name, name = get_script_url(movie)
        script_url = BASE_URL + urllib.parse.quote(script_url) + ".pdf"

        metadata[name] = {"file_name": file_name, "script_url": script_url}

        if metadata_only:
            continue

        if os.path.join(DIR, file_name + ".txt") in files:
            continue

        text = get_script_from_url(script_url, file_name)
        if text == "" or name == "":
            metadata.pop(name, None)
            continue

        with open(os.path.join(DIR, file_name + ".txt"), "w", errors="ignore") as out:
            out.write(text)

    with open(os.path.join(META_DIR, SOURCE + ".json"), "w") as outfile:
        json.dump(metadata, outfile, indent=4)
