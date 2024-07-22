import os

import openai
import config
os.environ["TESSDATA_PREFIX"] = config.TESSDATA_PREFIX
import re
import string
import urllib.request

import pymupdf
import textract
from bs4 import BeautifulSoup
from requests_html import HTMLSession
from tenacity import stop_after_attempt  # for exponential backoff
from tenacity import retry, wait_random_exponential
import base64

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

def clean_pdf_text(text):
    text = text.encode('utf-8', 'ignore').decode('utf-8').strip()
    text = text.replace("", "")
    text = text.replace("•", "")
    text = text.replace("·", "")
    return text

client = openai.OpenAI(
    api_key=config.OPENAI_API_KEY
)
@retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
def completion_with_backoff(**kwargs):
    return client.chat.completions.create(**kwargs)

# import easyocr
# print("Loading OCR engine...")
# reader = easyocr.Reader(['en']) 
# print("OCR engine loaded.")
# def ocr_image(image_bytes):
#     reader.readtext(image_bytes,paragraph=True)
#     result = reader.readtext(image_bytes,paragraph=True)
#     return "\n".join([l[1] for l in result]) 


def ocr_image(
    image_bytes,    
):    
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    response = completion_with_backoff(
        model="gpt-4o",
        temperature=0,        
        messages=[
            {
                "role": "system",
                "content": "Read the text in the image and return it verbatim.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            },
        ],
    )
    return response.choices[0].message.content.strip()


def get_pdf_text(url, name):
    doc = os.path.join("scripts", "temp", name + ".pdf")
    result = urllib.request.urlopen(url)
    f = open(doc, "wb")
    f.write(result.read())
    f.close()
    ocr = False
    try:
        doc = pymupdf.open(doc)
        text = ""
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            page_text = clean_pdf_text(page.get_text())
            if not page_text:
                img = page.get_pixmap()
                page_text = ocr_image(img.tobytes())                
                ocr = True

            text += page_text

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