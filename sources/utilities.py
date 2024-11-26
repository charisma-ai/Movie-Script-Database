import os

import openai
from tqdm.auto import tqdm

import config

os.environ["TESSDATA_PREFIX"] = config.TESSDATA_PREFIX
import base64
import re
import string
import urllib.request
# from transformers import AutoModel, AutoTokenizer
from typing import Any, Dict, List, Tuple
from uuid import UUID

import pandas as pd
import pymupdf
import textract
import tiktoken
from bs4 import BeautifulSoup
from langchain_community.cache import SQLiteCache
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.globals import set_llm_cache
from langchain_core.output_parsers import StrOutputParser
from langchain_core.outputs import LLMResult
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from requests_html import HTMLSession
from tenacity import stop_after_attempt  # for exponential backoff
from tenacity import retry, wait_random_exponential


def format_filename(s):
    valid_chars = "-() %s%s%s" % (string.ascii_letters, string.digits, "%")
    filename = "".join(c for c in s if c in valid_chars)
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


def clean_pdf_text(text):
    text = text.encode("utf-8", "ignore").decode("utf-8").strip()
    text = text.replace("", "")
    text = text.replace("•", "")
    text = text.replace("·", "")
    return text


client = openai.OpenAI(api_key=config.OPENAI_API_KEY)


@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def completion_with_backoff(**kwargs):
    return client.chat.completions.create(**kwargs)

def ocr_images(
    image_bytes: list[str],
    use_cache: bool = True,
    verbose=True,
) -> list[str]:
    if use_cache:
        set_llm_cache(SQLiteCache(database_path=".langchain.db"))
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    chain = (
        {
            "image_data": lambda x: x,
        }
        | ChatPromptTemplate.from_messages(
            [
                ("system", "Read the text in the image and return it verbatim."),
                ("user", [
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/jpeg;base64,{image_data}"},
                    }
                ]),
            ]
        )
        | llm
        | StrOutputParser()
    )

    if verbose:
        with BatchCallback(len(image_bytes), "OCRing images") as cb:
            ocred_imgs = chain.batch(
                image_bytes,
                {"max_concurrency": 20, "callbacks": [cb]},
            )
    else:
        ocred_imgs = chain.batch(
            image_bytes,
            {"max_concurrency": 20},
        )

    return ocred_imgs


def get_pdf_text(url, name):
    doc = os.path.join("scripts", "temp", name + ".pdf")
    result = urllib.request.urlopen(url)
    with open(doc, "wb") as f:
        f.write(result.read())
    ocr = False
    print(f"Processing {doc}...")
    text = ""
    try:
        doc = pymupdf.open(doc)
        imgs = []
        for page_num in tqdm(range(doc.page_count), total=doc.page_count):
            page = doc.load_page(page_num)
            page_text = clean_pdf_text(page.get_text())
            if not page_text or ocr:                
                ocr = True
                img = page.get_pixmap()
                base64_image = base64.b64encode(img.tobytes()).decode('utf-8')
                imgs.append(base64_image)
            if not ocr:
                text += page_text

        if ocr:
            page_texts = ocr_images(imgs)
            text = "".join(page_texts)

    except Exception as err:
        print(err)
        text = ""
    # if os.path.isfile(doc):
    #     os.remove(doc)
    if ocr:
        print(f"{name} was OCR'd - there might be errors!")
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


class BatchCallback(BaseCallbackHandler):
    def __init__(self, total: int, desc: str):
        super().__init__()
        self.count = 0
        self.progress_bar = tqdm(total=total, desc=desc)  # define a progress bar

    # Override on_llm_end method. This is called after every response from LLM
    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> Any:
        self.count += 1
        self.progress_bar.update(1)

    def __enter__(self):
        self.progress_bar.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self.progress_bar.__exit__(exc_type, exc_value, exc_traceback)

    def __del__(self):
        self.progress_bar.__del__()