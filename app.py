from flask import render_template, request, redirect, url_for
from math import ceil
from surfmining import *

PER_PAGE = 50

class Pagination(object):

    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        last = 0
        for num in xrange(1, self.pages + 1):
            if num <= left_edge or \
                (num > self.page - left_current - 1 and \
                 num < self.page + right_current) or \
                num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num


def get_users_for_page(accounts, page, per_page):
    #accounts = mongo.db.instagram.find({"deleted": {"$exists": False}}).sort("coin", -1)
    min_range = (page - 1) * per_page
    max_range = min_range + per_page
    return accounts[min_range:max_range]


def url_for_other_page(page):
    args = request.view_args.copy()
    args['page'] = page
    return url_for(request.endpoint, **args)
app.jinja_env.globals['url_for_other_page'] = url_for_other_page


def get_context(accounts, page):
    surfers = get_users_for_page(accounts, page, PER_PAGE)
    count = surfers.count()
    pagination = Pagination(page, PER_PAGE, count)
    if not surfers and page != 0:
        abort(404)
    return surfers, pagination


@app.route("/")
def home():
    return render_template("home.html")


@app.route('/instagram/rank-surfers', defaults={'page': 1}, methods=["GET"])
@app.route("/instagram/rank-surfers/<int:page>")
def instagram(page):

    accounts = mongo.db.instagram.find({"deleted": {"$exists": False}}).sort("coin", -1)
    surfers, pagination = get_context(accounts, page)
    return render_template("all_surfers.html", surfers=surfers, pagination=pagination)


@app.route("/instagram/confirmed-surfers", defaults={'page': 1}, methods=["GET"])
@app.route("/instagram/confirmed-surfers/<int:page>")
def instagram_confirmed_surfers(page):

    accounts = mongo.db.instagram.find({"surfing": True}).sort("F", -1)
    surfers, pagination = get_context(accounts, page)
    return render_template("approachable_surfers.html", surfers=surfers, pagination=pagination)


@app.route("/instagram/unconfirmed-surfers", defaults={'page': 1}, methods=["GET"])
@app.route("/instagram/unconfirmed-surfers/<int:page>")
def instagram_unconfirmed_surfers(page):
    accounts = mongo.db.instagram.find(
        {"$and": [{"deleted": {"$exists": False}},
                  {"surfing": {"$exists": False}}]},
                  ).sort("coin", -1)
    surfers, pagination = get_context(accounts, page)
    return render_template("unconfirmed_surfers.html", surfers=surfers, pagination=pagination)


@app.route("/instagram/set-state", methods=["POST"])
def set_state():
    referer = request.headers.get("Referer")
    state = request.form["state"]
    name = request.form["name"]
    print name, state
    if state == "True":
        state_ = True
        profile = scrape(name)
    else:
        state_ = False
    print state_
    mongo.db.instagram.update({"name": name}, {"$set": {"surfing": state_}}, multi=True)
    if referer == None:
        referer = '/instagram'
    return redirect(referer)


@app.route("/instagram/add-surfer", methods=["POST"])
def add_surfer():
    referer = request.headers.get("Referer")
    name = request.form["name"]
    profile = scrape(name)
    if referer == None:
        referer = '/'
    return redirect(referer)


@app.route("/instagram/delete", methods=["POST"])
def delete_surfer():

    if request.method == 'POST':
        name = request.form["name"]
        mongo.db.instagram.remove({"name": name})
        return redirect(url_for('instagram'))

if __name__ == "__main__":
    app.run(debug=True)
