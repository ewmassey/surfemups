import requests
from bs4 import BeautifulSoup
import re
import time
from flask import Flask
from flask.ext.pymongo import PyMongo
#import operator

app = Flask(__name__)
mongo = PyMongo(app)

FAME_THRESHOLD = 10000
CRAWL_PAGES = 3
DELAY = 0.5


def calculateF(followers, following):
    return float(following) / (int(followers) + 1)


def crawl_page(url, profile={}):

    webstagram_base = "http://web.stagram.com"

    r = requests.get(webstagram_base + url)

    soup = BeautifulSoup(r.content, "lxml")
    if not profile:
        m = re.search("^/n/(?P<name>\w+)", url)
        profile["name"] = m.group("name")
        info_block = soup.find("div", id="user_info")
        if info_block == None:
            profile["deleted"] = True
            print profile["name"], "is not active."
            return profile

        profile_info = info_block.find("div", style="margin-left:300px")
        profile["info"] = profile_info.text.strip()
        surfs = re.findall("surf", profile["info"].lower())
        if surfs:
            profile["surfing"] = True
        a = profile_info.find("a")
        if a:
            profile["link"] = a.attrs.get("href")
        else:
            profile["link"] = None

        profile["photo_count"] = info_block("tr")[2]("span", text=re.compile("\d+"))[0].text.strip()
        try:
            profile["followers"] = soup.find("span", id=re.compile("follower_count_\d+")).text
        except:
            profile["followers"] = 0

        try:
            profile["following"] = soup.find("span", id=re.compile("following_count_\d+")).text
        except:
            profile["followers"] = 0

        profile["F"] = calculateF(profile.get("followers"), profile.get("following"))
        #profile["photos"] = []
        profile["mentions"] = {}
        profile["pages"] = 1

    this_photos = soup(class_="photoeach")

    for photo in this_photos:
        photo_id = photo.attrs.get("id")
        id_ = photo_id[len("photo"):]
        ulist = photo.find("ul", class_=id_)
        if ulist:
            messages = ulist.find_all("li")
            for msg in messages:
                mentions = re.findall("@(\w+)", msg.text.strip())

                for mention in mentions:
                    m = profile["mentions"].get(mention)
                    if m:
                        profile["mentions"][mention] += 1
                    else:
                        profile["mentions"][mention.lower()] = 1

    next_link = soup.find("a", text="Earlier")
    time.sleep(DELAY)
    if next_link and (profile["pages"] < CRAWL_PAGES):
        next = next_link.attrs.get("href")
        profile["pages"] += 1
        return crawl_page(next, profile=profile)
    else:
        return profile


def spend_coin(acct):
    accts = mongo.db.instagram
    mentions = acct.get("mentions")
    total_mentions = float(sum(mentions.values()))
    #print mentions

    #print "tm", total_mentions
    """
    yes = 0
    no = 0
    maybe = 0
    yes1 = accts.find({"$and": [{"name": {"$in": mentions.keys()}}, {"surfing": True}]})
    no1 = accts.find({"$and": [{"name": {"$in": mentions.keys()}}, {"surfing": False}]})
    maybe1 = accts.find({"$and": [{"name": {"$in": mentions.keys()}}, {"surfing": {"$exists": False}}]})
    for y in yes1:
        name = y.get("name")
        yes += mentions.get(name)

    for n in no1:
        name = n.get("name")
        yes += mentions.get(name)

    for m in maybe1:
        name = m.get("name")
        maybe += mentions.get(name)

    here = sum([yes, no, maybe])
    dross = (total_mentions - here)

    #print yes, no, maybe, here, total_mentions, nope, dross
    """

    for k, v in acct.get("mentions").iteritems():

        ratio = 1
        if acct.get("photo_count") == None:

            continue
        if acct.get("surfing") == True:
            followers = int(acct.get("followers"))
            if followers > FAME_THRESHOLD:
                #Famous confirmed surfers get a bonus

                ratio *= followers / FAME_THRESHOLD
        elif acct.get("surfing") == False:
            ratio = 0
            continue
        else:
            #Unknown but crawled accounts are dampened
            ratio = 0.25

        spend = ratio * v / total_mentions
        #print k, spend
        accts.update({"$and": [{"name": k}, {"surfing": {"$nin": [False]}}]}, {"$set": {"name": k}, "$inc": {"coin": spend}}, upsert=True)


def rank(iterations=3):
    print "Ranking surfers..."
    start = time.time()
    accts = mongo.db.instagram
    count = accts.count()
    #surfer_count = accts.find({"surfing": True}).count()
    accts.update({"surfing": True}, {"$set": {"coin": 1}}, multi=True)
    accts.update({"$or": [{"surfing": False}, {"surfing": {"$exists": False}}]},
        {"$set": {"coin": 0}}, multi=True)
    #accts.update(
    #    {"surfing": {"$exists": False}}, {"$set": {"coin": 0}}, multi=True)
    """
    for surfer in accts.find({"surfing": True}):
        #print surfer.get("name")
        spend_coin(surfer)
    """
    for i in range(iterations):
        for acct in accts.find({"deleted": {"$exists": False}}).sort("coin", -1):
            "Spend Coin on all the other accounts"
            if acct.get("mentions"):
                spend_coin(acct)
    finished = time.time()
    print "Finished %d in %f seconds" % (count, (finished - start))
    #accts.update({"surfing": False}, {"$set": {"coin": 0}}, multi=True)


def add_to_crawl(names):
    accts = mongo.db.instagram
    if names:
        to_add = []
        for k in names:
            name = k.lower()
            exist_ = accts.find_one({"name": name})
            if exist_:
                pass
                #print "Don't have to recrawl %s" % exist_.get("name")
            else:
                to_add.append({"name": name.lower()})
        if to_add != []:
            mongo.db.instagram_to_crawl.insert(to_add)


def scrape(name):
    name = name.lower()
    url = "/n/%s" % name
    profile = crawl_page(url, profile={})
    surfing = profile.get("surfing")
    if surfing:
        add_to_crawl(profile.get("mentions").keys())
    mongo.db.instagram.update({"name": profile.get("name")}, profile, upsert=True)

    return profile
