import argparse
import json
import os
import time
from pathlib import Path

from tqdm import tqdm

import sources
from clean_files import clean_script
from sources.utilities import format_filename, get_pdf_text

DIR = Path(__file__).parent / "scripts/downloads"
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
    parser = argparse.ArgumentParser(
        description="Download scripts from list of urls and sources"
    )
    parser.add_argument(
        "--movies",
        type=Path,
        default="../charismatic-tools/storydb_scraper/data/movies.json",
        help="List of urls to download",
    )
    args = parser.parse_args()
    with open(args.movies, "r") as f:
        data = json.load(f)

    new_data = {k: v for k, v in data.items() if v.get("sources")}
    print(f"No sources found for {len(data)-len(new_data)} scripts")
    # data = new_data
    # new_data = {
    #     k: v
    #     for k, v in data.items()
    #     if not (DIR / (format_filename(k) + ".txt")).exists()
    # }
    # print(f"Scripts already downloaded for {len(data)-len(new_data)} scripts")
    # data = new_data

    failed = 0
    starttime = time.time()
    for name, d in tqdm(new_data.items()):
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
                download = sources.get_download_from_url_func(source)
                if download is not None:
                    try:
                        text = download(script_url, file_name)
                        text = clean_script(text).strip()
                        if text:
                            with open(save_name, "w") as f:
                                f.write(text)
                            text_found = True
                            break
                    except Exception as e:
                        print(e)
                        continue
        # fallback
        if not text_found and len(d["sources"]) != 0:
            script_url = d["sources"][0]["url"]
            if script_url.endswith(".pdf"):
                try:
                    text = get_pdf_text(script_url, file_name)
                    text = clean_script(text).strip()
                    if text:
                        with open(save_name, "w") as f:
                            f.write(text)
                        text_found = True
                except Exception:
                    text_found = False

        if not text_found:
            print("Script is empty: " + script_url)
            failed += 1

    print(f"Failed: {failed}")
    print("Time taken = {} seconds".format(time.time() - starttime))
