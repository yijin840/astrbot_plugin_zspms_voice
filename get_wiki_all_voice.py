import json

import requests
from bs4 import BeautifulSoup

base = "https://wiki.biligame.com"


def parseHrefHtml(title, url):
    resp = requests.get(url)
    # print(resp.text)
    soup = BeautifulSoup(resp.text, "lxml")
    dict = {}
    audios = soup.find_all("div", class_="media-audio")
    print(f"{title} : {len(audios)}")
    data_files = []
    if len(audios) > 0:
        for i in range(0, len(audios)):
            # print(str(i) + ": " + title + ": " + audios[i].get("data-file"))
            data_files.append(audios[i].get("data-file"))
    return data_files


def getHtml(url):
    resp = requests.get(url)
    # print(resp.text)
    # 解析
    voices_json = []
    soup = BeautifulSoup(resp.text, "lxml")
    for tabs in soup.find_all("div", class_="tab_con"):
        for tab in tabs.find_all("a"):
            title = tab.get("title")
            href = tab.get("href")
            voices_json.append({
                "title": title,
                "href": href,
                "voices": parseHrefHtml(title, base + href)
            })

    return voices_json


def main():
    url = "https://wiki.biligame.com/zspms/%E6%9C%BA%E4%BD%93%E5%9B%BE%E9%89%B4"
    voices_json = getHtml(url)
    # json写入到文件中
    with open("voices.json", "w", encoding="utf-8") as f:
        json.dump(voices_json, f, ensure_ascii=False, indent=4)
        print("写入完成")


main()
