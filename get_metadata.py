import json
import re
import string
from os import listdir
from os.path import getsize, isfile, join
from pathlib import Path

from fuzzywuzzy import fuzz
from imdb import Cinemagoer
from themoviedb import TMDb
from tqdm.std import tqdm
from unidecode import unidecode

import config

ia = Cinemagoer()


META_DIR = join("scripts", "metadata")
TMDB_MOVIE_URL = "https://api.themoviedb.org/3/search/movie?api_key=%s&language=en-US&query=%s&page=1"
TMDB_TV_URL = (
    "https://api.themoviedb.org/3/search/tv?api_key=%s&language=en-US&query=%s&page=1"
)
TMDB_ID_URL = "https://api.themoviedb.org/3/find/%s?api_key=%s&language=en-US&external_source=imdb_id"
tmdb_api_key = config.tmdb_api_key

forbidden = [
    "the",
    "a",
    "an",
    "and",
    "or",
    "part",
    "vol",
    "chapter",
    "movie",
    "transcript",
]


def clean_name(name):
    name = name.lower()
    # Split by "_"
    name = " ".join(name.split("_"))
    # Remove ", The" and ", A"
    name = name.replace(", the", "")
    name = name.replace(", a", "")
    name = re.sub(" +", " ", name).strip()

    # If name has filmed as or released as, use those names instead
    alt_name = name.split("filmed as")
    if len(alt_name) > 1:
        name = re.sub(r"[\([{})\]]", "", name).split("filmed as")[-1].strip()
    alt_name = name.split("released as")
    if len(alt_name) > 1:
        name = re.sub(r"[\([{})\]]", "", name).split("released as")[-1].strip()
    # Remove brackets ()
    name = re.sub(r"\([^)]*\)", "", name)
    # Remove "Early/Final Pilot TV Script PDF", "Script",
    # "Transcript", "Pilot", "First Draft"
    name = name.replace("early pilot", "")
    name = name.replace("final pilot", "")
    name = name.replace("transcript", "")
    name = name.replace("first draft", "")
    name = name.replace("tv script pdf", "")
    name = name.replace("pilot", "")
    name = name.strip()

    return name


def average_ratio(n, m):
    return (fuzz.token_sort_ratio(n, m) + fuzz.token_sort_ratio(m, n)) // 2


def roman_to_int(num):
    string = num.split()
    res = []
    for s in string:
        if s == "ii":
            res.append("2")
        elif s == "iii":
            res.append("3")
        elif s == "iv":
            res.append("4")
        elif s == "v":
            res.append("5")
        elif s == "vi":
            res.append("6")
        elif s == "vii":
            res.append("7")
        elif s == "viii":
            res.append("8")
        elif s == "ix":
            res.append("9")
        else:
            res.append(s)
    return " ".join(res)


def extra_clean(name):
    name = (
        roman_to_int(clean_name(name))
        .replace("the ", "")
        .replace("-", "")
        .replace(":", "")
        .replace("episode", "")
        .replace(".", "")
    )
    return name


tmdb = TMDb(key=config.tmdb_api_key)


def get_tmdb(name, type="movie"):
    if type == "movie":
        date = "release_date"
        title = "title"
    elif type == "tv":
        date = "first_air_date"
        title = "name"

    if type == "movie":
        results = tmdb.search().movies(name)
    elif type == "tv":
        results = tmdb.search().tv(name)

    if len(results) > 0:
        result = results[0]
        if type == "movie":
            result = tmdb.movie(result.id).details(
                append_to_response="credits,external_id,keywords"
            )
        elif type == "tv":
            result = tmdb.tv(result.id).details(
                append_to_response="credits,external_id,keywords"
            )

        directors = [p.name for p in result.credits.crew if p.job == "Director"]
        cast = [
            {"character": p.character, "actor": p.name}
            for p in result.credits.cast[:10]
        ]  # get 10 main characters

        release_date = getattr(result, date, None)
        release_date = release_date.strftime("%Y-%m-%d") if release_date else None

        return {
            "tmbd_id": result.id,
            "imdb_id": getattr(result, "imdb_id", None),
            "title": getattr(result, title, None),
            "release_date": release_date,
            "overview": result.overview,
            "tagline": result.tagline,
            "genres": ",".join(g.name for g in result.genres),
            "keywords": ",".join(g.name for g in result.keywords.keywords),
            "cast": cast,
            "directors": ",".join(directors),
        }
    else:
        return {}


def get_tmdb_from_id(id):
    jres = tmdb.find().by_tvdb(id)
    o_type = None
    if len(jres["movie_results"]) > 0:
        results = "movie_results"
        date = "release_date"
        title = "title"
        o_type == "movie"
    elif len(jres["tv_results"]) > 0:
        results = "tv_results"
        date = "first_air_date"
        title = "name"
        o_type == "tv"
    else:
        return {}

    result = jres[results][0]
    if o_type == "movie":
        result = tmdb.movie(result.id).details(
            append_to_response="credits,external_id,keywords"
        )
    elif o_type == "tv":
        result = tmdb.tv(result.id).details(
            append_to_response="credits,external_id,keywords"
        )
    else:
        return {}

    directors = [p.name for p in result.credits.crew if p.job == "Director"]
    cast = [
        {"character": p.character, "actor": p.name} for p in result.credits.cast[:10]
    ]  # get 10 main characters

    release_date = getattr(result, date, None)
    release_date = release_date.strftime("%Y-%m-%d") if release_date else None

    return {
        "tmbd_id": result.id,
        "imdb_id": getattr(result, "imdb_id", None),
        "title": getattr(result, title, None),
        "release_date": release_date,
        "overview": result.overview,
        "tagline": result.tagline,
        "genres": ",".join(g.name for g in result.genres),
        "keywords": ",".join(g.name for g in result.keywords.keywords),
        "cast": cast,
        "directors": ",".join(directors),
    }


def get_imdb(name):
    try:
        movies = ia.search_movie(name)
        if len(movies) > 0:
            movie_id = movies[0].movieID
            movie = movies[0]

            if "year" in movie:
                release_date = movie["year"]
            else:
                print("Field missing in response")
                return {}

            return {
                "id": movie_id,
                "title": unidecode(movie["title"]),
                "release_date": release_date,
                "director": movie["directors"],
                "plot": movie["plot"],
                "plot outline": movie["plot outline"],
                "keywords": movie["keywords"],
                "genres": movie["genres"],
                "taglines": movie["taglines"],
                "synopsis": movie["synopsis"],
            }
        else:
            return {}
    except Exception as err:
        print(err)
        return {}


if __name__ == "__main__":
    metadata = {}
    f = open("sources.json", "r")
    data = json.load(f)
    metadata_path = Path(META_DIR) / "clean_meta.json"
    interval = 10

    for source in data:
        included = data[source]
        meta_file = join(META_DIR, source + ".json")
        if included == "true" and isfile(meta_file):
            with open(meta_file) as json_file:
                source_meta = json.load(json_file)
                metadata[source] = source_meta

    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            origin = json.load(f)
    else:
        unique = []
        origin = {}
        for source in metadata:
            DIR = join("scripts", "unprocessed", source)
            files = [
                join(DIR, f)
                for f in listdir(DIR)
                if isfile(join(DIR, f)) and getsize(join(DIR, f)) > 3000
            ]

            source_meta = metadata[source]
            for script in source_meta:
                name = re.sub(r"\([^)]*\)", "", script.strip()).lower()
                name = " ".join(name.split("-"))
                name = re.sub(r"[" + string.punctuation + "]", " ", name)
                name = re.sub(" +", " ", name).strip()
                name = name.split()
                name = " ".join(list(filter(lambda a: a not in forbidden, name)))
                name = "".join(name.split())
                name = roman_to_int(name)
                name = unidecode(name)
                unique.append(name)
                if name not in origin:
                    origin[name] = {"files": []}
                curr_script = metadata[source][script]
                curr_file = join(
                    "scripts", "unprocessed", source, curr_script["file_name"] + ".txt"
                )
                m = {
                    "name": unidecode(script),
                    "source": source,
                    "file_name": curr_script["file_name"],
                    "script_url": curr_script["script_url"],
                }

                if curr_file in files:
                    m["size"] = getsize(curr_file)

                origin[name]["files"].append(m)

        final = sorted(list(set(unique)))
        print(len(final))

    if not metadata_path.exists():
        print("Saving intermediate metadata...")
        with open(metadata_path, "w") as outfile:
            json.dump(origin, outfile, indent=4)

    print("Get metadata from TMDb")

    count = 0
    for i, script in tqdm(enumerate(origin), total=len(origin)):
        if origin[script].get("tmdb"):
            continue

        # Use original name
        name = origin[script]["files"][0]["name"]
        movie_data = get_tmdb(name)

        if movie_data:
            origin[script]["tmdb"] = movie_data

        else:
            # Try with cleaned name
            name = extra_clean(name)
            movie_data = get_tmdb(name)

            if movie_data:
                origin[script]["tmdb"] = movie_data

            else:
                # Try with TV search
                tv_data = get_tmdb(name, "tv")

                if tv_data:
                    origin[script]["tmdb"] = tv_data

                else:
                    print(name)
                    count += 1

        if (i + 1) % (len(origin) // interval) == 0:
            print("Saving intermediate TMDB metadata...")
            with open(metadata_path, "w") as outfile:
                json.dump(origin, outfile, indent=4)

    print(count)

    print("Saving intermediate metadata with TMDB data...")
    with open(metadata_path, "w") as outfile:
        json.dump(origin, outfile, indent=4)

    print("Get metadata from IMDb")

    count = 0
    for i, script in tqdm(enumerate(origin), total=len(origin)):
        if origin[script].get("imdb"):
            continue
        name = origin[script]["files"][0]["name"]
        movie_data = get_imdb(name)

        if not movie_data:
            name = extra_clean(name)
            movie_data = get_imdb(name)

            if not movie_data:
                print(name)
                count += 1
            else:
                origin[script]["imdb"] = movie_data
        else:
            origin[script]["imdb"] = movie_data

        if (i + 1) % (len(origin) // interval) == 0:
            print("Saving intermediate IMDB metadata...")
            with open(metadata_path, "w") as outfile:
                json.dump(origin, outfile, indent=4)

    print(count)
    print("Saving intermediate metadata with IMDB data...")
    with open(metadata_path, "w") as outfile:
        json.dump(origin, outfile, indent=4)

    # Use IMDb id to search TMDb
    count = 0
    print("Use IMDb id to search TMDb")

    for script in tqdm(origin):
        if "imdb" in origin[script] and "tmdb" not in origin[script]:
            # print(origin[script]["files"][0]["name"])
            imdb_id = "tt" + origin[script]["imdb"]["id"]
            movie_data = get_tmdb_from_id(imdb_id)
            if movie_data:
                origin[script]["tmdb"] = movie_data

            else:
                print(origin[script]["imdb"]["title"], imdb_id)
                count += 1

    with open(join(META_DIR, "clean_meta.json"), "w") as outfile:
        json.dump(origin, outfile, indent=4)

    print(count)

    count = 0
    print("Identify and correct names")

    for script in tqdm(origin):
        if "imdb" in origin[script] and "tmdb" in origin[script]:
            imdb_name = extra_clean(unidecode(origin[script]["imdb"]["title"]))
            tmdb_name = extra_clean(unidecode(origin[script]["tmdb"]["title"]))
            file_name = extra_clean(origin[script]["files"][0]["name"])

            if (
                imdb_name != tmdb_name
                and average_ratio(file_name, tmdb_name) < 85
                and average_ratio(file_name, imdb_name) > 85
            ):
                imdb_id = "tt" + origin[script]["imdb"]["id"]
                movie_data = get_tmdb_from_id(imdb_id)
                if movie_data:
                    origin[script]["tmdb"] = movie_data

                else:
                    print(origin[script]["imdb"]["title"], imdb_id)
                    count += 1

            if (
                imdb_name != tmdb_name
                and average_ratio(file_name, tmdb_name) > 85
                and average_ratio(file_name, imdb_name) < 85
            ):
                name = origin[script]["tmdb"]["title"]
                movie_data = get_imdb(name)

                if not movie_data:
                    name = extra_clean(name)
                    movie_data = get_imdb(name)

                    if not movie_data:
                        print(name)
                        count += 1
                    else:
                        origin[script]["imdb"] = movie_data
                else:
                    origin[script]["imdb"] = movie_data

    print(count)
    print("Saving final metadata")
    with open(metadata_path, "w") as outfile:
        json.dump(origin, outfile, indent=4)
