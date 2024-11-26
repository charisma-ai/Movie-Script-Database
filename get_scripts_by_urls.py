import argparse
import json
import multiprocessing
import os
import shutil
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


def download_scripts(data: dict, output: Path):
    failed = 0
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

        sources_list = {
            s["source"]: s.get("script_url", s.get("url"))
            for s in d.get("sources", d.get("files", []))
        }
        sources_list = [
            {"source": x, "url": sources_list[x]} for x in PRIORITY if x in sources_list
        ]  # sort by priority
        text_found = False
        for source in sources_list:
            script_url = source.get("url", source.get("script_url"))
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
        if not text_found and len(d.get("sources", d.get("files", []))) != 0:
            script_url = d.get("sources", d.get("files", []))[0].get(
                "url", d.get("sources", d.get("files", []))[0].get("script_url")
            )
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

        if text_found:
            output.mkdir(parents=True, exist_ok=True)
            output_path = output / save_name.name
            shutil.copy2(save_name, output_path)
        else:
            print("Script is empty: " + script_url)
            failed += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download scripts from list of urls and sources"
    )
    parser.add_argument(
        "--movies",
        type=Path,
        default="new_movies.json",
        help="List of urls to download",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default="scripts/output",
        help="Output folder",
    )
    parser.add_argument(
        "--num_processes",
        type=int,
        default=10,
        help="Number of processes",
    )
    args = parser.parse_args()
    with open(args.movies, "r") as f:
        data = json.load(f)

    new_data = {k: v for k, v in data.items() if v.get("sources", v.get("files"))}
    print(f"No sources found for {len(data)-len(new_data)} scripts")

    failed = 0
    starttime = time.time()
    processes: list[multiprocessing.Process] = []

    batch_size = len(new_data) // args.num_processes
    print(f"Batch size: {batch_size}")
    data_list = list(new_data.items())
    for i in range(args.num_processes):
        data = dict(data_list[i * batch_size : (i + 1) * batch_size])
        p = multiprocessing.Process(target=download_scripts, args=(data, args.output))
        processes.append(p)
        p.start()

    for process in processes:
        process.join()

    print(f"Failed: {failed}")
    print("Time taken = {} seconds".format(time.time() - starttime))
