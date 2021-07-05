#!/usr/bin/env python

import os
import sys
import re
import requests
import tmdbsimple as tmdb
from bs4 import BeautifulSoup

TMDB_KEY = os.environ.get("TMDB_KEY")
OMDB_KEY = os.environ.get("OMDB_KEY")


def get_movie(title="", year="", tmdb_id="", imdb_id=""):
    tmdb.API_KEY = TMDB_KEY

    movie_id = tmdb_id
    if not movie_id:
        search = tmdb.Search()
        res = search.movie(query=title, year=year, page=1)

        try:
            movie_id = res["results"][0]["id"]
        except (IndexError, KeyError):
            return None

    movie_result = tmdb.Movies(movie_id)
    movie = movie_result.info()
    omdb = get_omdb_data(movie["imdb_id"])
    year = f'{movie["release_date"][:4]}' if movie["release_date"] else ""
    alternative_titles = [
        i["title"]
        for i in movie_result.alternative_titles()["titles"]
        if i["iso_3166_1"] in ["GB", "US"]
    ]

    rottentomatoes_rating = omdb["rottentomatoes_rating"]
    if rottentomatoes_rating[0] == "Not found":
        rottentomatoes_rating = get_rottentomatoes_rating(movie["title"], year)

    metacritic_rating = omdb["metacritic_rating"]
    if metacritic_rating[0] == "Not found":
        metacritic_rating = get_metacritic_rating(movie["title"], year)

    letterboxd_rating = get_letterboxd_rating(movie_id, movie["title"], year)

    filmaffinity_rating = get_filmaffinity_rating(
        movie["title"], movie["original_title"], alternative_titles, year
    )

    return {
        "title": movie["title"],
        "original_title": movie["original_title"],
        "alternative_titles": alternative_titles,
        "year": year,
        "imdb-id": movie["imdb_id"],
        "imdb-rating": omdb["imdb_rating"],
        "rotten-tomatoes-rating": rottentomatoes_rating,
        "metacritic-rating": metacritic_rating,
        "letterboxd-rating": letterboxd_rating,
        "tmdb-id": movie_id,
        "tmdb-rating": [
            str(movie["vote_average"]) + "/10",
            float(movie["vote_average"]),
        ]
        if movie["vote_count"] > 0
        else ["Not found", -1],
        "filmaffinity-rating": filmaffinity_rating,
    }


def get_omdb_data(imdb_id):
    try:
        url = f"http://www.omdbapi.com/?apikey={OMDB_KEY}&i={imdb_id}"
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    movie = response.json()

    try:
        imdb = movie["Ratings"][0]["Value"]
        imdb = [imdb, float(imdb.split("/")[0])]
    except (IndexError, KeyError, ValueError, TypeError):
        imdb = ["Not found", -1]

    try:
        rotten_tomatoes = movie["Ratings"][1]["Value"]
        rotten_tomatoes = [rotten_tomatoes, float(rotten_tomatoes[:-1]) / 10]
    except (IndexError, KeyError, ValueError, TypeError):
        rotten_tomatoes = ["Not found", -1]

    try:
        metacritic = movie["Ratings"][2]["Value"]
        metacritic = [metacritic, float(metacritic.split("/")[0]) / 10]
    except (IndexError, KeyError, ValueError, TypeError):
        metacritic = ["Not found", -1]

    return {
        "imdb_rating": imdb,
        "rottentomatoes_rating": rotten_tomatoes,
        "metacritic_rating": metacritic,
    }


def get_rottentomatoes_rating(title, year):
    rating = ["Not found", -1]

    if not year:
        return rating

    req_count = 0
    while req_count < 3:
        next_page = ""
        url = f"https://www.rottentomatoes.com/napi/search/all?type=movie\
            &searchQuery={title}&after={next_page}"

        try:
            res = requests.get(url)
            data = res.json()
            req_count += 1
        except requests.RequestException:
            return rating

        if not data["movies"]:
            break

        for movie in data["movies"]["items"]:
            try:
                if movie["name"] == title and movie["releaseYear"] == year:
                    if movie["tomatometerScore"]:
                        rating = movie["tomatometerScore"]["score"]
                        rating = [f"{rating}%", float(rating) / 10]
                    break
            except (KeyError, ValueError, TypeError):
                continue

        if not data["movies"]["pageInfo"]["endCursor"]:
            break
        next_page = data["movies"]["pageInfo"]["endCursor"]

        if rating:
            break

    return rating


def get_metacritic_rating(title, year):
    url = f"https://www.metacritic.com/search/movie/{title}/results"
    rating = None
    user_agent = "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 \
        (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.37"

    if not year:
        return ["No found", -1]

    try:
        res = requests.get(url, headers={"User-Agent": user_agent})
        soup = BeautifulSoup(res.text, "html.parser")
        results = soup.find_all("div", class_="result_wrap")
    except requests.RequestException:
        return ["No found", -1]

    for movie in results:
        t = movie.a.text.strip()
        y = movie.p.text.strip()[-4:]
        if t == title and y == year:
            rating = movie.span.text
            break

    try:
        return [f"{rating}/100", float(rating) / 10]
    except (TypeError, ValueError):
        return ["Not found", -1]


def get_letterboxd_rating(tmdb_id, title="", year=""):
    try:
        search_res = requests.get(f"https://letterboxd.com/tmdb/{tmdb_id}")
        search_soup = BeautifulSoup(search_res.text, "html.parser")
        movie_rating = round(
            float(
                search_soup.find_all(attrs={"name": "twitter:data2"})[0][
                    "content"
                ].split()[0]
            ),
            1,
        )
        return [str(movie_rating) + "/5", movie_rating * 2]
    except (
        requests.RequestException,
        IndexError,
        KeyError,
        ValueError,
        AttributeError,
    ):
        return ["Not found", -1]


def get_filmaffinity_rating(title, original_title, alternative_titles, year):
    def clean(title):
        title = title.lower().replace("the", "").strip()
        title = re.sub(r"[\(\[].*?[\)\]]|[^a-z0-9]", "", title)
        return title

    url = f"https://www.filmaffinity.com/en/search.php?stype=title\
        &stext={title}"
    rating = None
    title = clean(title)
    original_title = clean(original_title)

    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
    except requests.RequestException:
        return ["Not found", -1]

    results = soup.find_all("div", class_="se-it mt")

    if results:
        try:
            for movie in results:
                t = movie.find_all("a")[1].get("title").strip()
                y = movie.find("div", class_="ye-w").text
                titles = [title, original_title]

                if (clean(t) in titles
                        or t in alternative_titles) and y == year:
                    rating = movie.find("div", class_="avgrat-box").text
                    break
        except (IndexError, AttributeError):
            pass
    else:
        try:
            t = soup.find_all("h1", {"id": "main-title"})[0].text
            ot = clean(
                soup.find_all("dl", class_="movie-info")[0].dd.contents[0]
            )
            y = soup.find_all("dd", {"itemprop": "datePublished"})[0].text
            titles = [clean(t), ot]
            try:
                for i in soup.find_all("dd", class_="akas")[0]\
                        .ul.find_all("li"):
                    titles.append(clean(i.text))
            except (IndexError, AttributeError):
                pass

            if year == y and (
                title in titles
                or original_title in titles
                or t in alternative_titles
            ):
                rating = soup.find_all("div", {"id": "movie-rat-avg"})[0]\
                    .text.strip()
        except (IndexError, AttributeError):
            pass

    try:
        return [f"{rating}/10", float(rating)]
    except (ValueError, TypeError):
        return ["Not found", -1]


def get_average_rating(movie):
    rating_sum = 0
    rating_count = 0

    for key in movie:
        if "rating" in key and movie[key][1] > 0:
            rating_sum += movie[key][1]
            rating_count += 1

    if rating_count > 0:
        return round(rating_sum / rating_count, 1)
    return 'No rating'


def format_rating(site, rating):
    spaces = f"{' ' * (25 - len(rating) - len(site))}"
    return f"{site} rating:{spaces + rating}"


if len(sys.argv) not in [2, 3]:
    print("\nUsage: ./movie_ratings.py <movie_title> [<release_year>]\n")
    sys.exit(0)

title = sys.argv[1]
year = ""

if len(sys.argv) == 3:
    year = sys.argv[2]
    print(f'\nSearching for "{title} {year}"...')
else:
    print(f'\nSearching for "{title}"...')

movie = get_movie(title, year)
if not movie:
    print("\nMovie not found.\n")
    sys.exit(0)

average_rating = get_average_rating(movie)


print(
    f"\n\n{movie['title']} ({movie['year']})\n\n"
    f"{format_rating('IMDb', movie['imdb-rating'][0])}\n"
    f"{format_rating('RottenTomatoes', movie['rotten-tomatoes-rating'][0])}\n"
    f"{format_rating('Metacritic', movie['metacritic-rating'][0])}\n"
    f"{format_rating('Letterboxd', movie['letterboxd-rating'][0])}\n"
    f"{format_rating('TMDb', movie['tmdb-rating'][0])}\n"
    f"{format_rating('FilmAffinity', movie['filmaffinity-rating'][0])}\n\n"
    f"{format_rating('Average', str(average_rating))}\n"
)
