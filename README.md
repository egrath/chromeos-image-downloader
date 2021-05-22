# Google Chrome OS Wallpaper Image downloader

This little project aims to download all of the available wallpapers from Chrome OS.

## Usage
### Prerequisites
You should always use a virtual environment to not pollute your Python installation.


Linux:
```
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

Windows:
```
python -m venv venv
env\scripts\activate
pip install -r requirements.txt
```

### Run
```
python down.py
```
will download all currently available wallpapers from the Google servers into corresponding directories.
