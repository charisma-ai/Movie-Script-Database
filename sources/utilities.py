import os
import re
import string
import urllib.request

import textract
from bs4 import BeautifulSoup
from requests_html import HTMLSession


def format_filename(s):
    valid_chars = "-() %s%s%s" % (string.ascii_letters, string.digits, "%")
    filename = "".join(c for c in s if c in valid_chars)
    filename = filename.replace("%20", " ")
    filename = filename.replace("%27", "")
    filename = filename.replace(" ", "-")
    filename = re.sub(r"-+", "-", filename).strip()
    return filename


s = HTMLSession()


def get_soup(url):
    try:
        response = s.get(url)
        response.html.render()
        resulttext = response.html.html

        soup = BeautifulSoup(resulttext, "html.parser")

    except Exception as err:
        print(err)
        soup = None
    return soup


def get_pdf_text(url, name):
    doc = os.path.join("scripts", "temp", name + ".pdf")
    result = urllib.request.urlopen(url)
    f = open(doc, "wb")
    f.write(result.read())
    f.close()
    try:
        text = textract.process(doc, encoding="utf-8").decode("utf-8")
    except Exception as err:
        print(err)
        text = ""
    # if os.path.isfile(doc):
    #     os.remove(doc)
    return text


def get_doc_text(url, name):
    doc = os.path.join("scripts", "temp", name + ".doc")
    result = urllib.request.urlopen(url)
    f = open(doc, "wb")
    f.write(result.read())
    f.close()
    try:
        text = textract.process(doc, encoding="utf-8").decode("utf-8")
    except Exception as err:
        print(err)
        text = ""
    # if os.path.isfile(doc):
    #     os.remove(doc)
    return text


def create_script_dirs(source):
    DIR = os.path.join("scripts", "unprocessed", source)
    TEMP_DIR = os.path.join("scripts", "temp", source)
    META_DIR = os.path.join("scripts", "metadata")

    if not os.path.exists(DIR):
        os.makedirs(DIR)
    if not os.path.exists(META_DIR):
        os.makedirs(META_DIR)
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    return DIR, TEMP_DIR, META_DIR
