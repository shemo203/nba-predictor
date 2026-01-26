import requests
import bs4
import json
import datetime
import nbastats


response = requests.get(url = "https://basketball.realgm.com/")
soup = bs4.BeautifulSoup(response.text, "html.parser")

article_list = [article.find(class_ = "article-title").getText() for article in soup.find_all(class_ = "secondary-story")]
article_list.insert(0, soup.find(class_ = "lead-story").getText())

nba_wiretap = {
    "entry": {
        "time" :  datetime.datetime.now().isoformat(),
        "source" : "RealGM",
        "action_list" : article_list
    }
}

try:
    with open("data.json", "r") as data_file:
        data = json.load(data_file)
        data.update(nba_wiretap)
except FileNotFoundError:
    with open("data.json", "w") as data_file:
        json.dump(nba_wiretap, data_file, indent = 4)
else:
    with open("data.json", "w") as data_file:
        json.dump(nba_wiretap, data_file, indent = 4)

print(article_list)


