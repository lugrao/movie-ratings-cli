#!/usr/bin/env python

import os
import sys
import re
import requests
import tmdbsimple as tmdb
from bs4 import BeautifulSoup

TMDB_KEY = os.environ.get('TMDB_KEY')
OMDB_KEY = os.environ.get('OMDB_KEY')


def get_movie(title='', year='', tmdb_id='', imdb_id=''):
    tmdb.API_KEY = TMDB_KEY

    movie_id = tmdb_id
    if not movie_id:
        search = tmdb.Search()
        res = search.movie(query=title, year=year, page=1)

        try:
            movie_id = res['results'][0]['id']
        except:
            return None

    movie_result = tmdb.Movies(movie_id)
    movie = movie_result.info()
    movie_credits = movie_result.credits()
    omdb = get_omdb_data(movie['imdb_id'])
    year = f'{movie["release_date"][:4]}' if movie['release_date'] else ''
    alternative_titles = [i['title'] for i in movie_result.alternative_titles()[
        'titles'] if i['iso_3166_1'] in ['GB', 'US']]
    letterboxd_rating = get_letterboxd_rating(
        movie_id, movie['title'], year)
    filmaffinity_rating = get_filmaffinity_rating(
        movie['title'], movie['original_title'], alternative_titles, year)

    movie_data = {
        'title': movie['title'],
        'original_title': movie['original_title'],
        'alternative_titles': alternative_titles,
        'year': year,
        'imdb-id': movie['imdb_id'],
        'imdb-rating': omdb['imdb_rating'],
        'rotten-tomatoes-rating': omdb['rotten_tomatoes_rating'],
        'metacritic-rating': omdb['metacritic_rating'],
        'letterboxd-rating': letterboxd_rating,
        'tmdb-id': movie_id,
        'tmdb-rating': [str(movie['vote_average']) + '/10', float(movie['vote_average'])] if movie['vote_count'] > 0 else ['Not found', -1],
        'filmaffinity-rating': filmaffinity_rating
    }

    return movie_data


def get_omdb_data(imdb_id):

    try:
        url = f'http://www.omdbapi.com/?apikey={OMDB_KEY}&i={imdb_id}'
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException:
        return None

    movie = response.json()

    try:
        imdb = movie['Ratings'][0]['Value']
        imdb = [imdb, float(imdb.split('/')[0])]
    except (IndexError, ValueError, KeyError):
        imdb = ['Not found', -1]

    try:
        rotten_tomatoes = movie['Ratings'][1]['Value']
        rotten_tomatoes = [rotten_tomatoes, float(rotten_tomatoes[:-1]) / 10]
    except (IndexError, ValueError, KeyError):
        rotten_tomatoes = ['Not found', -1]

    try:
        metacritic = movie['Ratings'][2]['Value']
        metacritic = [metacritic, float(metacritic.split('/')[0]) / 10]
    except (IndexError, ValueError, KeyError):
        metacritic = ['Not found', -1]

    return {
        'imdb_rating': imdb,
        'rotten_tomatoes_rating': rotten_tomatoes,
        'metacritic_rating': metacritic,
    }


def get_letterboxd_rating(tmdb_id, title='', year=''):
    try:
        search_res = requests.get(f'https://letterboxd.com/tmdb/{tmdb_id}')
        search_soup = BeautifulSoup(search_res.text, 'html.parser')
        movie_rating = round(float(search_soup.find_all(
            attrs={'name': 'twitter:data2'})[0]['content'].split()[0]), 1)

        return [str(movie_rating) + '/5', movie_rating * 2]
    except:
        return ['Not found', -1]


def get_filmaffinity_rating(title, original_title, alternative_titles, year):
    def clean(title):
        title = title.lower().replace('the', '').strip()
        title = re.sub(r'[\(\[].*?[\)\]]|[^a-z0-9]', '', title)
        return title

    url = f'https://www.filmaffinity.com/en/search.php?stype=title&stext={title}'
    rating = None
    title = clean(title)
    original_title = clean(original_title)

    try:
        res = requests.get(url)
        soup = BeautifulSoup(res.text, 'html.parser')
    except:
        return ['Not found', -1]

    results = soup.find_all('div', class_='se-it mt')

    if results:
        try:
            for movie in results:
                t = movie.find_all('a')[1].get('title').strip()
                y = movie.find('div', class_='ye-w').text
                titles = [title, original_title]

                if (clean(t) in titles or t in alternative_titles) and y == year:
                    rating = movie.find('div', class_='avgrat-box').text
                    break
        except:
            pass
    else:
        try:
            t = soup.find_all('h1', {'id': 'main-title'})[0].text
            ot = clean(soup.find_all('dl', class_='movie-info')
                       [0].dd.contents[0])
            y = soup.find_all('dd', {'itemprop': 'datePublished'})[0].text
            titles = [clean(t), ot]
            try:
                for i in soup.find_all('dd', class_='akas')[0].ul.find_all('li'):
                    titles.append(clean(i.text))
            except:
                pass

            if year == y and (title in titles or original_title in titles or t in alternative_titles):
                rating = soup.find_all(
                    'div', {'id': 'movie-rat-avg'})[0].text.strip()
        except:
            pass

    try:
        return [f'{rating}/10', float(rating)]
    except:
        return ['Not found', -1]


if len(sys.argv) not in [2, 3]:
    print("\nUsage: ./movie_ratings.py <movie_title> [<release_year>]\n")
    sys.exit(0)

title = sys.argv[1]
year = ''

if len(sys.argv) == 3:
    year = sys.argv[2]
    print(f'\nSearching for "{title} {year}"...')
else:
    print(f'\nSearching for "{title}"...')

movie = get_movie(title, year)
if not movie:
    print("\nMovie not found.\n")
    sys.exit(0)

print(f"\n\n{movie['title']} ({movie['year']})\n"
      f"\nIMDb rating:...................{movie['imdb-rating'][0]}\n"
      f"RottenTomatoes rating:.........{movie['rotten-tomatoes-rating'][0]}\n"
      f"Metacritic rating:.............{movie['metacritic-rating'][0]}\n"
      f"Letterboxd rating:.............{movie['letterboxd-rating'][0]}\n"
      f"TMDb rating:...................{movie['tmdb-rating'][0]}\n"
      f"FilmAffinity rating:...........{movie['filmaffinity-rating'][0]}\n")
