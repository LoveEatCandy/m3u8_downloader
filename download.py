import logging
import os
import shutil
import subprocess
from concurrent.futures import ProcessPoolExecutor
from urllib import parse

import requests
from Crypto.Cipher import AES
from retry import retry

import m3u8

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HEADERS = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    "Connection": "keep-alive",
    "Origin": "https://player.yunbtv.cc",
    "sec-ch-ua": '"Chromium";v="112", "Microsoft Edge";v="112", "Not:A-Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36 Edg/112.0.1722.34",
}
TMP_DIR = ".tmp"
VIDEO_DIR = "videos"

session = requests.session()
session.headers = HEADERS
session.verify = False
session.get = retry(tries=10, delay=1)(session.get)


def download_ts(url, file_path, m3u8_key):
    try:
        if os.path.exists(file_path):
            return

        content = session.get(url, timeout=10).content

        if m3u8_key:
            parser = parse.urlparse(url)
            key_url = (
                m3u8_key.uri
                if m3u8_key.uri.startswith("http")
                else "".join([parser.scheme, "://", parser.hostname, m3u8_key.uri])
            )
            key = session.get(key_url, timeout=10).content
            cipher = AES.new(key, AES.MODE_CBC, IV=None)
            content = cipher.decrypt(content)

        with open(file_path, "wb") as f:
            f.write(content)
        logger.info(f"downloaded {file_path}")
    except Exception as e:
        logger.exception("download")
        raise e


def download_hls_and_convert_to_mp4(
    urls, max_workers: int = 32, auto_clean: bool = True
):
    for name, url in urls.items():
        parser = parse.urlparse(url)
        hostname = parser.hostname
        current_tmp_dir = os.path.join(TMP_DIR, name)
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            os.makedirs(current_tmp_dir, exist_ok=True)
            m3u8_obj = m3u8.load(url, headers=HEADERS, verify_ssl=False)
            for index, segment in enumerate(m3u8_obj.segments, start=1):
                ts_url = segment.uri
                if not ts_url.startswith("http"):
                    ts_url = "".join([parser.scheme, "://", hostname, ts_url])
                ts_file_path = os.path.join(current_tmp_dir, f"{index}.ts".zfill(8))
                executor.submit(download_ts, ts_url, ts_file_path, m3u8_obj.keys[0])

        merged_ts_path = os.path.join(TMP_DIR, f"{name}.ts")
        with open(merged_ts_path, "wb") as merged_ts:
            for file_name in sorted(list(os.listdir(current_tmp_dir))):
                with open(os.path.join(current_tmp_dir, file_name), "rb") as single_ts:
                    merged_ts.write(single_ts.read())

        os.makedirs(VIDEO_DIR, exist_ok=True)
        video_path = os.path.join(VIDEO_DIR, f"{name}.mp4")
        subprocess.run(
            ["ffmpeg", "-i", merged_ts_path, "-map", "0", "-c", "copy", video_path]
        )
        if auto_clean:
            shutil.rmtree(current_tmp_dir)
            os.unlink(merged_ts_path)


if __name__ == "__main__":
    urls = {
        "9": "https://vod11.bdzybf7.com/20230408/MBf8eBAS/2000kb/hls/index.m3u8",
    }
    download_hls_and_convert_to_mp4(urls, max_workers=32)
