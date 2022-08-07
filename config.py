NAVIGATE_BASE_URL = "https://www.oldbookillustrations.com/illustrations"
PAGES = 350
ILLUSTRATIONS_URLS = "urls.txt"
ILLUSTRATIONS_INFO_CSV = "illustrations.csv"
CACHE_DIR = "cache"

clean = True
task_list = [
    "prepare_illustration_list",
    "download_illustrations",
    "check_failed_downloads",
]
task_id = 1
task = task_list[task_id]
