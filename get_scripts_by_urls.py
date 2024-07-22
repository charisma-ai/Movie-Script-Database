import json
import os
import time
from pathlib import Path

from tqdm import tqdm

import sources
from clean_files import clean_script
from sources.utilities import format_filename

DIR = Path("scripts") / "downloads"
DIR.mkdir(parents=True, exist_ok=True)

PRIORITY = [
    "awesomefilm",
    "screenplays",
    "dailyscript",
    "sfy",
    "imsdb",
    "scriptslug",
    "scriptsavant",
    "scriptpdf",
]
if __name__ == "__main__":
    with open("movies.json", "r") as f:
        data = json.load(f)

    new_data = {k: v for k, v in data.items() if v.get("sources")}
    print(f"No sources found for {len(data)-len(new_data)} scripts")
    data = new_data
    # new_data = {
    #     k: v
    #     for k, v in data.items()
    #     if not (DIR / (format_filename(k) + ".txt")).exists()
    # }
    # print(f"Scripts already downloaded for {len(data)-len(new_data)} scripts")
    data = new_data

    failed = 0
    starttime = time.time()
    for name, d in tqdm(data.items()):
        file_name = format_filename(name)
        save_name = DIR / (file_name + ".txt")
        if save_name.exists():
            with open(save_name, "r") as f:
                text = f.read()
                text = clean_script(text).strip()
                if text:
                    continue
                else:
                    os.remove(save_name)

        sources_list = {s["source"]: s["url"] for s in d.get("sources", [])}
        sources_list = [
            {"source": x, "url": sources_list[x]} for x in PRIORITY if x in sources_list
        ]  # sort by priority
        text_found = False
        for source in sources_list:
            script_url = source.get("url")
            source = source.get("source")
            if script_url and source:
                text = sources.get_download_from_url_func(source)(script_url, file_name)
                text = clean_script(text).strip()
                if text:
                    with open(save_name, "w") as f:
                        f.write(text)
                    text_found = True
                    break
        if not text_found:
            print("Script is empty: " + script_url)
            failed += 1

    print(f"Failed: {failed}")
    print("Time taken = {} seconds".format(time.time() - starttime))
