import json
import time
from pathlib import Path

from tqdm import tqdm

import sources
from sources.utilities import format_filename

DIR = Path("scripts") / "downloads"
DIR.mkdir(parents=True, exist_ok=True)
if __name__ == "__main__":
    with open("urls.json", "r") as f:
        data = json.load(f)

    starttime = time.time()
    for name, d in tqdm(data.items()):
        script_url = d.get("script_url")
        if script_url:
            source = d["source"]
            file_name = format_filename(name)
            if (DIR / (file_name + ".txt")).exists():
                continue
            text = sources.get_download_from_url_func(source)(script_url, file_name)
            if not text:
                print("Script is empty: " + script_url)
                continue
            with open(DIR / (file_name + ".txt"), "w") as f:
                f.write(text)

    print()
    print("Time taken = {} seconds".format(time.time() - starttime))
