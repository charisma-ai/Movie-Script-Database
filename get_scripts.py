import json
import multiprocessing
import os
import time

import config
import sources

DIR = os.path.join("scripts", "temp")

if not os.path.exists(DIR):
    os.makedirs(DIR)

if __name__ == "__main__":
    f = open("sources.json", "r")
    data = json.load(f)
    processes = []
    starttime = time.time()

    for source in data:
        included = data[source]
        if included == "true":
            # print("Fetching scripts from %s" % (source))
            # sources.get_scripts(source=source)
            # print()
            p = multiprocessing.Process(
                target=sources.get_scripts, args=(source, config.metadata_only)
            )
            processes.append(p)
            p.start()

    for process in processes:
        process.join()

    print()
    print("Time taken = {} seconds".format(time.time() - starttime))
