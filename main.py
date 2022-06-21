from source import *
from flask import *
import enum
import os
import time

from logger import logging
from bs4 import BeautifulSoup
import requests
import re
import webbrowser
import argparse

port = "2096"
cimaclub = f"https://www.cima-club.io/"


class Type(enum.Enum):
    movie = 1
    series = 2


def extract_season_number(season_title: str, with_proxy):
    match = re.search(r"موسم [0-9]+", season_title)
    if not bool(match):
        return season_title
    if match.group().split()[1].isdigit():
        return match.group().split()[1]
    return match.group()



def get_episodes_links(season_link: str, with_proxy):
    if season_link.endswith("/"):
        season_link = season_link[:-1]

    response = requests.get(season_link + "/episodes")

    content = BeautifulSoup(response.text, "html.parser")
    episodes_div = content.select('div[class*="media-block"] > div[class="content-box"]')
    if len(episodes_div) == 0:
        logging.error("could not extract episode links from found season link")
        return []
    episodes_links = [None] * len(episodes_div)
    for i in episodes_div:
        if i.span.em is not None and i.a["href"] is not None:
            episodes_links[int(i.span.em.text) - 1] = i.a["href"]
    while episodes_links[-1] is None:
        episodes_links.pop()
    return episodes_links


def generate_list_of_links_to_download(chosen_episode, episodes) -> list:
    if chosen_episode == "all":
        first_episode = 1
        last_episode = len(episodes)
    else:
        string = chosen_episode.split("-")
        first_episode = int(string[0])
        last_episode = int(string[1])
        if first_episode < 1 or last_episode > len(episodes):
            raise RuntimeError("the fist episode must be > 1 and the last one must be within the range of the season")
    for i in range(first_episode - 1, last_episode):
        if episodes[i] is not None:
            episodes[i] = episodes[i].replace("episode", "watch")
    return episodes[first_episode - 1:last_episode]



def get_download_links(url: str, with_proxy):
    """
    :param with_proxy:
    :param url: the download link - should be in the form : https://www.cima-club.cc:..../watch/....
    :return: a list of the download links --> watch out, there will be other links in there
    """

    response = requests.get(url)
    content = BeautifulSoup(response.text, "html.parser")
    downloads_links = content.select_one('div[class*="downloads"]')
    if downloads_links is None:
        logging.error("downloads section not found, please choose a different episode/movie to download")
        logging.error("to exit please click ctrl+c")
        raise RuntimeError()
    download_link = ""
    for i in downloads_links.findChildren("a"):
        if "gvid" in i["href"] or "govid" in i["href"]:
            download_link = i["href"]
            break
    if download_link == "":
        logging.error("download link not found, please choose a different episode/movie to download")
        logging.error("to exit please click ctrl+c")
        raise RuntimeError()  # gvid links not found


    req = requests.get(download_link, headers={'referer': 'https://cima-club.io/'})
    if not str(req.status_code).startswith("2"):
        logging.error("govid server is unreachable")
        return []
    download_page = BeautifulSoup(req.text, 'html.parser')
    L = []
    for i in download_page.find_all("a"):
        L.append(i["href"])
    return L

def searchall(title: str, movie_or_series: Type, with_proxy=False):

    search_result = BeautifulSoup(requests.get(cimaclub + "search", params={"s": title}).text, 'html.parser')
    links = []
    titles = []
    for i in search_result.select('div[class*="media-block"] > div'):
        a = i.find_all('a')[-1]
        if movie_or_series == Type.movie and "series" not in a["href"] and 'season' not in a["href"]:
            links.append(a["href"])
            titles.append(a.text)
        elif movie_or_series == Type.series and 'season' in a["href"]:
            links.append(a["href"])
            titles.append(a.text)
    assert len(links) == len(titles)

    #####
    links_dict = dict()
    for i in range(len(titles)):
        links_dict[titles[i]] = links[i]
    sort_links = dict(sorted(links_dict.items(), key=lambda x: extract_season_number(x[0], with_proxy), reverse=False))
    links = list(sort_links.values())
    titles = list(sort_links.keys())
    for i in range(len(titles)):
        print(f"{titles[i]} : ({i + 1})")




def beautify_download_links(links: list):
    quality_link = {}
    for i in links:
        if "-240" in i:
            quality_link["240"] = i
        elif "-360" in i:
            quality_link["360"] = i
        elif "-480" in i:
            quality_link["480"] = i
        elif "-720" in i:
            quality_link["720"] = i
        elif "-1080" in i:  # aac-1080
            quality_link["1080"] = i
    if list(quality_link.keys()) == []:
        raise RuntimeError("no links found")
    return quality_link


def best_quality_link(links: dict):
    L = []
    for i in links.keys():
        if str(i).isnumeric():
            L.append(int(i))
    return str(max(L))



def save_in_txt(quality, links_list, title):
    mylinks = {}
    mylinks["download links"]=[]
    if quality == 'best':
        for links in links_list:
            mylinks["download links"].append(links[best_quality_link(links)])
        print(mylinks)
        return mylinks
    else:
        for links in links_list:
            mylinks["download links"].append(links[quality])
            print(mylinks)
            return mylinks


def choose_multiple_quality(qualities: set, links_list: list, title: str,qualtytoShose: str):
    quality = qualtytoShose
    if quality == 'best' or quality in qualities:
           return save_in_txt(quality, links_list, title)


def searchonemovie(chosen: int,title: str, movie_or_series: Type, with_proxy=False ):


    search_result = BeautifulSoup(requests.get(cimaclub + "search", params={"s": title}).text, 'html.parser')
    links = []
    titles = []
    for i in search_result.select('div[class*="media-block"] > div'):
        a = i.find_all('a')[-1]
        if movie_or_series == Type.movie and "series" not in a["href"] and 'season' not in a["href"]:
            links.append(a["href"])
            titles.append(a.text)
        elif movie_or_series == Type.series and 'season' in a["href"]:
            links.append(a["href"])
            titles.append(a.text)
    assert len(links) == len(titles)

    #####
    links_dict = dict()
    for i in range(len(titles)):
        links_dict[titles[i]] = links[i]
    sort_links = dict(sorted(links_dict.items(), key=lambda x: extract_season_number(x[0], with_proxy), reverse=False))
    links = list(sort_links.values())
    titles = list(sort_links.keys())

    a = links[chosen]
    if movie_or_series == Type.movie:
        a = a.replace("film", "watch")
    elif 'season' in a:
        episodes = get_episodes_links(a, with_proxy)
        chosen_episode = input(f"please choose an episode : (1-{len(episodes)}) or 'all': ")
        # case of all episodes in one season || multiple episodes
        logging.debug(f"chosen ep : {chosen_episode}--{bool(re.compile('[1-9]+-[1-9]+').match(chosen_episode))} ")
        if chosen_episode == "all" or bool(re.compile('[1-9]+-[1-9]+').match(chosen_episode)):
            return generate_list_of_links_to_download(chosen_episode, episodes)
        chosen_episode = int(chosen_episode)
        while not (0 < chosen_episode <= len(episodes)):
            print("err :::::: " + f"the chosen must be between 1 and {len(episodes)}")
            chosen_episode = int(input(f"please choose an episode : (1-{len(episodes)}) : "))
        a = episodes[chosen_episode - 1]
        if a is not None:
            a = a.replace("episode", "watch")
    return a


app = Flask(__name__)
@app.route('/searchmovie/',methods=['GET'])
def give_me_show():
    link = searchall(request.args.get('name'), Type.movie, False)
    print(link)

@app.route('/searchonemovie/',methods=['GET'])
def givethatshow():
    with_proxy=False
    title=request.args.get('name')
    link = searchonemovie(int(request.args.get('number')),title, Type.movie, with_proxy)
    if not isinstance(link, list):
        download_links = []
        qualities = []
        links = beautify_download_links(get_download_links(link, with_proxy))
        download_links.append(links)
        qualities.append(list(links.keys()))
        return choose_multiple_quality(set.intersection(*map(set, qualities)), download_links, title,"best")





if __name__ == "__main__":
    app.debug=True
    app.run()