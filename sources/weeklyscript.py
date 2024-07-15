import json
import os
import re
import urllib

from tqdm import tqdm

from .utilities import create_script_dirs, format_filename, get_pdf_text, get_soup


def get_weeklyscript(metadata_only=True):
    ALL_URL = "https://www.weeklyscript.com/movies_full_list.htm"
    BASE_URL = "https://www.weeklyscript.com/"
    SOURCE = "weeklyscript"
    DIR, TEMP_DIR, META_DIR = create_script_dirs(SOURCE)

    if not os.path.exists(DIR):
        os.makedirs(DIR)

    soup = get_soup(ALL_URL)
    movielist = soup.find_all("center")[0].find_all("a")[2:]

    # print(len(movielist))
    metadata = {}
    for movie in tqdm(movielist):
        script_url = movie.get("href")
        text = ""

        if script_url.endswith(".pdf"):
            name = script_url.split("/")[-1].split(".pdf")[0]
        elif script_url.endswith(".html"):
            name = script_url.split("/")[-1].split(".html")[0]
        elif script_url.endswith(".htm"):
            name = script_url.split("/")[-1].split(".htm")[0]
        elif script_url.endswith(".txt"):
            name = script_url.split("/")[-1].split(".txt")[0]

        metadata[name] = {"file_name": name, "script_url": script_url}
        if metadata_only:
            continue

        if script_url.endswith(".pdf"):
            text = get_pdf_text(BASE_URL + urllib.parse.quote(script_url))
        else:
            script_soup = get_soup(
                BASE_URL
                + urllib.parse.quote(
                    script_url.replace(".txt", ".html"), safe="%/:=&?~#+!$,;'@()*[]"
                )
            )
            center = script_soup.find_all("center")[0]
            unwanted = (
                center.find_all("div")
                + center.find_all("script")
                + center.find_all("ins")
            )
            for tag in unwanted:
                tag.extract()
            text = center.get_text().strip()

        if text == "" or name == "":
            continue

        name = re.sub(r"\([^)]*\)", "", format_filename(name)).strip()

        with open(os.path.join(DIR, name + ".txt"), "w", errors="ignore") as out:
            out.write(text)

    with open(os.path.join(META_DIR, SOURCE + ".json"), "w") as outfile:
        json.dump(metadata, outfile, indent=4)
