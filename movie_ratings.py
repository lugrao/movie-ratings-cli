#!/usr/bin/env python

import os
import re
import requests
import sys
import tmdbsimple as tmdb
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

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
        except Exception:
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
        "tmdb-rating": (
            [
                str(movie["vote_average"]) + "/10",
                float(movie["vote_average"]),
            ]
            if movie["vote_count"] > 0
            else ["Not found", -1]
        ),
        "filmaffinity-rating": filmaffinity_rating,
    }


def get_omdb_data(imdb_id):
    try:
        url = f"http://www.omdbapi.com/?apikey={OMDB_KEY}&i={imdb_id}"
        response = requests.get(url)
        response.raise_for_status()
    except Exception:
        return None

    movie = response.json()

    try:
        imdb = movie["Ratings"][0]["Value"]
        imdb = [imdb, float(imdb.split("/")[0])]
    except Exception:
        imdb = ["Not found", -1]

    try:
        rotten_tomatoes = movie["Ratings"][1]["Value"]
        rotten_tomatoes = [rotten_tomatoes, float(rotten_tomatoes[:-1]) / 10]
    except Exception:
        rotten_tomatoes = ["Not found", -1]

    try:
        metacritic = movie["Ratings"][2]["Value"]
        metacritic = [metacritic, float(metacritic.split("/")[0]) / 10]
    except Exception:
        metacritic = ["Not found", -1]

    return {
        "imdb_rating": imdb,
        "rottentomatoes_rating": rotten_tomatoes,
        "metacritic_rating": metacritic,
    }


def get_rottentomatoes_rating(title, year):
    rating = ["Not found", -1]
    movie_url = f"https://www.rottentomatoes.com/search?search={title}"

    if not year:
        return rating

    try:
        res = requests.get(movie_url)
        soup = BeautifulSoup(res.text, "html.parser")
        movies = soup.find_all(type="movie")[0].find_all("search-page-media-row")
    except Exception as e:
        print(e)
        return rating

    try:
        for movie in movies:
            movie_name = movie.find_all("a")[-1].text.strip()
            movie_score = movie.attrs["tomatometerscore"]
            release_year = movie.attrs["releaseyear"]

            if movie_name == title and release_year == year:
                rating = [f"{movie_score}%", float(movie_score) / 10]
                break
    except Exception:
        pass

    return rating


def get_metacritic_rating(title, year):
    url = f"https://www.metacritic.com/search/{title}/"
    rating = None
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.37"
    )

    if not year:
        return ["Not found", -1]

    try:
        res = requests.get(url, headers={"User-Agent": user_agent})
        soup = BeautifulSoup(res.text, "html.parser")
        movies = soup.find_all(
            "a",
            class_=lambda css_class: css_class is not None
            and css_class in "c-pageSiteSearch-results-item",
        )
    except Exception as e:
        print(e)
        return ["Not found", -1]

    for movie in movies:
        t = movie.find("p").text.strip().lower()
        y = movie.find_all("span")[2].text.strip()
        is_movie = "movie" == movie.find_all("span")[0].text.strip().lower()

        if t == title.lower() and y == year and is_movie:
            rating = movie.find_all("span")[-1].text.strip()
            movie_url = f"https://www.metacritic.com{movie['href']}"
            break

    try:
        return [f"{rating}/100", float(rating) / 10]
    except Exception as e:
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
    except Exception:
        return ["Not found", -1]


def get_filmaffinity_rating(title, original_title, alternative_titles, year):
    def clean(title):
        title = title.lower().replace("the", "").strip()
        title = re.sub(r"[\(\[].*?[\)\]]|[^a-z0-9]", "", title)
        return title

    url = f"https://www.filmaffinity.com/en/search.php?stext={title}"
    rating = None
    title = clean(title)
    original_title = clean(original_title)

    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, "html.parser")
    except Exception:
        return ["Not found", -1]

    results = soup.find_all("li", class_="se-it")

    if results:
        try:
            for movie in results:
                t = movie.find_all("div", class_="mc-title")[0].a.text.strip()
                y = movie.find_all("span", class_="mc-year")[0].text.strip()
                titles = [title, original_title]

                if (clean(t) in titles or t in alternative_titles) and y == year:
                    rating = movie.find("div", class_="avg").text.strip()
                    break
        except Exception:
            pass
    else:
        try:
            t = soup.find_all("h1", {"id": "main-title"})[0].text
            ot = clean(soup.find_all("dl", class_="movie-info")[0].dd.contents[0])
            y = soup.find_all("dd", {"itemprop": "datePublished"})[0].text
            titles = [clean(t), ot]
            try:
                for i in soup.find_all("dd", class_="akas")[0].ul.find_all("li"):
                    titles.append(clean(i.text))
            except Exception:
                pass

            if year == y and (
                title in titles or original_title in titles or t in alternative_titles
            ):
                rating = soup.find_all("div", {"id": "movie-rat-avg"})[0].text.strip()
        except Exception:
            pass

    try:
        return [f"{rating}/10", float(rating)]
    except Exception:
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
    return "No rating"


def format_rating(site, rating):
    spaces = f"{' ' * (25 - len(rating) - len(site))}"
    return f"{site} rating:{spaces + rating}"


def main():
    usage_message = (
        "Usage:\n"
        "  python movie_ratings.py title [year]\n"
        "\nExamples:\n"
        "  python movie_ratings.py Zerkalo\n"
        '  python movie_ratings.py "Poor Things"\n'
        "  python movie_ratings.py 'Nueve reinas' 2000\n"
        "  python movie_ratings.py Mononoke\\ Hime 1997\n"
    )

    if len(sys.argv) not in [2, 3]:
        print(usage_message)
        sys.exit(1)

    title = sys.argv[1]
    year = ""

    if len(sys.argv) == 3:
        try:
            year = sys.argv[2]
            int(year)
            if len(year) != 4:
                raise ValueError
        except ValueError:
            print("\nError: The second input must be a four digit number.\n\n")
            print(usage_message)

            sys.exit(1)
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
        f"{format_rating('RottenTomatoes', movie['rotten-tomatoes-rating'][0])}\
            \n"
        f"{format_rating('Metacritic', movie['metacritic-rating'][0])}\n"
        f"{format_rating('Letterboxd', movie['letterboxd-rating'][0])}\n"
        f"{format_rating('TMDb', movie['tmdb-rating'][0])}\n"
        f"{format_rating('FilmAffinity', movie['filmaffinity-rating'][0])}\n\n"
        f"{format_rating('Average', str(average_rating))}\n"
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExited on keyboard interrupt.")
