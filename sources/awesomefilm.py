import json
import os
import re
import urllib

from tqdm import tqdm

from .utilities import (
    create_script_dirs,
    format_filename,
    get_doc_text,
    get_pdf_text,
    get_soup,
)

SOURCE = "awesomefilm"
ALL_URL = "http://www.awesomefilm.com/"
BASE_URL = "http://www.awesomefilm.com/"

DIR, TEMP_DIR, META_DIR = create_script_dirs(SOURCE)


def get_script_from_url(script_url, file_name):
    if script_url.endswith(".pdf"):
        text = get_pdf_text(script_url, os.path.join(SOURCE, file_name))

    elif script_url.endswith(".doc"):
        text = get_doc_text(script_url, os.path.join(SOURCE, file_name))

    elif script_url.endswith(".txt"):
        f = urllib.request.urlopen(script_url)
        text = f.read().decode("utf-8", errors="ignore")

    else:
        script_soup = get_soup(script_url)
        page = script_soup.pre
        if page:
            text = page.get_text()

    return text


def get_awesomefilm(metadata_only=True):
    files = [
        os.path.join(DIR, f)
        for f in os.listdir(DIR)
        if os.path.isfile(os.path.join(DIR, f))
        and os.path.getsize(os.path.join(DIR, f)) > 3000
    ]
    metadata = {}
    soup = get_soup(ALL_URL)
    movielist = list(set(soup.find_all("td", class_="tbl")))

    def clean_name(name):
        name = re.sub(" +", " ", name)
        name = re.sub("\n", " ", name)
        name = re.sub(r"\([^)]*\)", "", name).strip()
        name = name.rstrip("script").strip()
        return name

    for movie in tqdm(movielist, desc=SOURCE):
        script_ele = movie.a
        if not script_ele:
            continue

        ele_url = script_ele.get("href")
        script_url = BASE_URL + urllib.parse.quote(ele_url)

        text = ""
        name = clean_name(script_ele.text)
        file_name = format_filename(name)

        metadata[name] = {"file_name": file_name, "script_url": script_url}
        if metadata_only:
            continue

        if os.path.join(DIR, file_name + ".txt") in files:
            continue

        try:
            text = get_script_from_url(script_url, file_name)
        except Exception as err:
            print(script_url)
            print(err)
            metadata.pop(name, None)
            continue

        if text == "":
            metadata.pop(name, None)
            continue

        with open(os.path.join(DIR, file_name + ".txt"), "w", errors="ignore") as out:
            out.write(text)

    with open(os.path.join(META_DIR, SOURCE + ".json"), "w") as outfile:
        json.dump(metadata, outfile, indent=4)
