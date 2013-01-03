from flask.ext.script import Manager
from surfmining import *

manager = Manager(app)


@manager.command
def rank_surfers():
    rank()


@manager.command
def crawl(all_=False, keep_crawling=False):
    "crawl instagram depth of one"
    if all_:
        accts = mongo.db.instagram.find()
        for acct in accts:
            mongo.db.instagram_to_crawl.update(
                {"name": acct.get("name")},
                {"name": acct.get("name")},
                upsert=True
                )
    to_crawl = mongo.db.instagram_to_crawl.find()
    crawl_count = to_crawl.count()
    print "scraping %d accounts" % crawl_count
    crawl = True
    while crawl == True:
        for acct in mongo.db.instagram_to_crawl.find():
            crawl_count -= 1
            print "Scraping ", acct.get("name"), "remaining: ", crawl_count
            scrape(acct.get("name"))
            mongo.db.instagram_to_crawl.remove(acct)
        if keep_crawling:
            count = mongo.db.instagra_to_crawl.find().count()
            if count > 0:
                print "keep crawling!"
            else:
                crawl = False
        else:
            crawl = False


@manager.command
def refresh_crawl():
    "refresh current accounts but don't dive"
    accts = mongo.db.instagram
    for a in accts.find():
        print "refreshing", a.get("name")
        state = a.get("surfing")
        url = "/n/%s" % a.get("name")
        profile = crawl_page(url, profile={})
        if state == True:
            profile["surfing"] = True
        if state == False:
            profile["surfing"] = False
        mongo.db.instagram.insert(profile)


@manager.command
def list_all():
    "print account names"
    print "Listing..."
    accts = mongo.db.instagram
    for a in accts.find().sort("coin", -1):
        print a.get("name"), a.get("surfing"), a.get("coin")


@manager.command
def list_to_crawl(count=False):
    "print the list of people left to crawl"
    to_crawl = mongo.db.instagram_to_crawl.find()
    crawl_count = to_crawl.count()
    if count:
        print "count =", crawl_count
    else:
        print "Listing to crawl..."

        print "remaining: ", crawl_count
        for a in to_crawl:
            print a.get("name")


@manager.command
def reset_to_crawl():
    "delete all to crawl"
    to_crawl = mongo.db.instagram_to_crawl
    for a in to_crawl.find():
        print "delete", a.get("name")
        to_crawl.remove({"id_": a.get("ObjectID")})


@manager.command
def delete_all():
    "delete all captured"
    accts = mongo.db.instagram
    for a in accts.find():
        print "delete", a.get("name")
        mongo.db.instagram.remove({"id_": a.get("ObjectID")})


@manager.command
def add_entry(name):
    profile = scrape(name)


@manager.command
def clean_up_here():
    accts = mongo.db.instagram.find()
    for acct in accts:
        followers = acct.get("followers")
        following = acct.get("following")
        if followers and following:
            F = calculateF(followers, following)
            mongo.db.instagram.update({"name": acct.get("name")},
                {"$set": {"F": F}})


@manager.command
def duplicates():
    #accts = mongo.db.instagram.find()
    for acct in mongo.db.instagram.find():
        name = acct.get("name")
        multis = mongo.db.instagram.find({"name": name})
        if multis.count() > 1:
            print name, multis.count()
            #mongo.db.instagram.remove({"name": name})

if __name__ == "__main__":
    manager.run()
