import hashlib
import logging
import os
import sys
from pathlib import Path
from typing import List

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from config import (
    CACHE_DIR,
    ILLUSTRATIONS_INFO_CSV,
    ILLUSTRATIONS_URLS,
    NAVIGATE_BASE_URL,
    PAGES,
    clean,
    task,
)


def try_remove(filename: str) -> None:
    try:
        os.remove(filename)
    except Exception:
        pass


def prepare():
    if clean:
        try_remove(ILLUSTRATIONS_URLS)
        try_remove("scraper.log")

    logging.basicConfig(
        format="%(asctime)s %(levelname)s: %(message)s",
        filename="scraper.log",
        level=logging.INFO,
    )


def get_url_content(url, allow_redirects=False):
    content = b""
    if not url:
        return content
    url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()
    filename = f"{CACHE_DIR}/{url_hash}"
    Path(CACHE_DIR).mkdir(exist_ok=True)

    if os.path.exists(filename):
        logging.info(f"Cache hit: url={url} filename={url_hash}")
        with open(filename, "rb") as f:
            return f.read()

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
    }

    logging.info(f"Cache miss: url={url} filename={url_hash}")
    try:
        response = requests.get(url, headers=headers)
    except Exception as e:
        logging.warning(f"Failed to download url={url} exception={e}")
        return content

    if response.status_code != 200:
        logging.warning(
            f"Failed to download url={url} status_code={response.status_code}"
        )
        if response.status_code == 429:
            sys.exit(f"status_code={response.status_code} Too Many Requests")
        return content

    if response.url.startswith(url):
        content = response.content
    else:
        logging.warning(f"orig_url={url} redirected_to={response.url}")

    with open(filename, "wb") as f:
        f.write(content)
    return content


def find_illust_urls(content) -> List[str]:
    soup = BeautifulSoup(content, "html.parser")
    # import pdb; pdb.set_trace()
    gallery = soup.find_all("ul", "archive-gallery")[0]
    illust_urls = set(a["href"] for a in gallery.find_all("a"))
    logging.info(f"Found {len(illust_urls)} illustrations")
    return list(illust_urls)


def prepare_illustration_list():
    prepare()
    urls = []
    # Process the first page
    logging.info("Processing page 1")
    content = get_url_content(NAVIGATE_BASE_URL)
    urls.extend(find_illust_urls(content))
    for page in range(2, PAGES + 1):
        logging.info(f"Processing page {page}")
        url = f"{NAVIGATE_BASE_URL}/page/{page}"
        content = get_url_content(url)
        urls.extend(find_illust_urls(content))
    with open(ILLUSTRATIONS_URLS, "w") as f:
        f.write("\n".join(urls))


def download_illustration(url: str):
    Path("images").mkdir(exist_ok=True)

    content = get_url_content(url)
    if not content:
        print("Failed to download", url)
        return
    soup = BeautifulSoup(content, "html.parser")
    download_link = soup.find("p", id="highres-dld").find_all("a")[-2]["href"]
    artist_def = soup.find("dd", "artist-deflist")
    artist_name = artist_def.find("span", itemprop="name").getText()
    description = soup.find_all("div", "img-description")[0].find_all("p")
    description = "\n".join(p.getText() for p in description)
    caption = soup.find("figcaption", itemprop="caption").getText()
    print("Downloading", url)
    img_url = f"https://www.oldbookillustrations.com{download_link}"
    illustration_info = {
        "artist_name": artist_name,
        "description": description,
        "caption": caption,
        "img_url": img_url,
        "url": url,
        "id": 0,
    }
    df = pd.DataFrame(illustration_info, index=[0])
    if os.path.exists(ILLUSTRATIONS_INFO_CSV):
        df = pd.concat([pd.read_csv(ILLUSTRATIONS_INFO_CSV), df])
    image = get_url_content(img_url)
    with open(f"images/{len(df)}.jpg", "wb") as f:
        f.write(image)
    df.reset_index()
    df["id"] = range(len(df))
    df.to_csv(
        ILLUSTRATIONS_INFO_CSV,
        index=False,
        columns=["id", "artist_name", "caption", "url", "description"],
    )


def download_illustrations():
    try:
        df = pd.read_csv("illustrations.csv")
        already_downloaded = len(df)
    except Exception:
        already_downloaded = 0
    urls = open(ILLUSTRATIONS_URLS).read().splitlines()[already_downloaded:]
    for url in tqdm(urls):
        download_illustration(url)


def check_failed_downloads():
    df = pd.read_csv(ILLUSTRATIONS_INFO_CSV)
    df["id"] = df["id"] + 1
    df.to_csv(ILLUSTRATIONS_INFO_CSV, index=False)
    # urls = open(ILLUSTRATIONS_URLS).read().splitlines()
    # illustrations = pd.read_csv(ILLUSTRATIONS_INFO_CSV)
    # failed_downloads = set(urls) - set(illustrations["url"])

    # for url in tqdm(failed_downloads):
    #     download_illustration(url)


def main():
    if task == "prepare_illustration_list":
        prepare_illustration_list()
    elif task == "download_illustrations":
        download_illustrations()
    elif task == "check_failed_downloads":
        check_failed_downloads()


if __name__ == "__main__":
    main()
