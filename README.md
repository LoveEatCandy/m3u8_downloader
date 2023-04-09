Download m3u8 and convert to mp4 with multiprocessing.
===
### Quick start

#### Clone
```
git clone https://github.com/LoveEatCandy/m3u8_downloader.git
pip3 install -r requirements.txt
```

#### Install ffmpeg
- Ubuntu
    ```
    sudo apt update
    sudo apt install -y ffmpeg
    ```

#### Update final part of `download.py` like:

```
if __name__ == "__main__":
    urls = {
        "file_name_with_out_suffix": "https://path/to/m3u8/index.m3u8",
    }
    download_hls_and_convert_to_mp4(urls, max_workers=32)
```

#### Finally

```
python3 download.py
```

#### You will find videos with name that you set in dir `videos`.