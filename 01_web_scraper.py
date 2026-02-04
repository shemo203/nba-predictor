import requests
import bs4
import json
import datetime
import nba_api

response = requests.get(url = "https://basketball.realgm.com/")
soup = bs4.BeautifulSoup(response.text, "html.parser")

article_list = [article.find(class_ = "article-title").getText() for article in soup.find_all(class_ = "secondary-story")]
article_list.insert(0, soup.find(class_ = "lead-story").getText())

history = []
nba_wiretap =   {
        "time" :  datetime.datetime.now().isoformat(),
        "source" : "RealGM",
        "action_list" : article_list
    }

try:
    with open("data.json", "r") as data_file:
        data = json.load(data_file)
except FileNotFoundError:
    with open("data.json", "w") as data_file:
        json.dump([nba_wiretap], data_file, indent = 4)
else:
    data.append(nba_wiretap)
    with open("data.json", "w") as data_file:
        json.dump(data, data_file, indent = 4)




