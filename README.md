# Movie Ratings CLI

A minimal CLI version of [Movie Ratings](https://movie-ratings.vercel.app/).

## Set up

Clone repository:

```
$ git clone https://github.com/lugrao/movie-ratings-cli.git
```

Go to repository directory:

```
$ cd movie-ratings-cli
```

Install dependencies:

```
$ pip install -r requirements.txt
```

Or with `pipenv`:

```
$ pipenv install -r requirements.txt
```

Get your TMDB API key [here](https://developers.themoviedb.org/3/getting-started/introduction), 
and your OMDB API key [here](http://www.omdbapi.com/apikey.aspx).

Export them as environment variables:

```
$ export TMDB_KEY=<your_TMDB_key>
$ export OMDB_KEY=<your_OMDB_key>
```

Or simply store them in `TMDB_KEY` and `OMDB_KEY` at lines 10 and 11 of `movie_ratings.py`.

## Usage

Search movie by title:

```
$ python movie_ratings.py Rocky

Searching for "Rocky"...


Rocky (1976)

IMDb rating:               8.1/10
RottenTomatoes rating:        92%
Metacritic rating:         70/100
Letterboxd rating:          4.0/5
TMDb rating:               7.8/10
FilmAffinity rating:       7.1/10

Average rating:               7.9
```

Search movie by title and year:

```
$ python movie_ratings.py Batman 1989

Searching for "Batman 1989"...


Batman (1989)

IMDb rating:               7.5/10
RottenTomatoes rating:        71%
Metacritic rating:         69/100
Letterboxd rating:          3.6/5
TMDb rating:               7.2/10
FilmAffinity rating:       6.8/10

Average rating:               7.1
```

If you're using `pipenv`:

```
$ pipenv run python movie_ratings.py 'The Godfather'

Searching for "The Godfather"...


The Godfather (1972)

IMDb rating:               9.2/10
RottenTomatoes rating:        97%
Metacritic rating:        100/100
Letterboxd rating:          4.5/5
TMDb rating:               8.7/10
FilmAffinity rating:       9.0/10

Average rating:               9.3
```
