## chuninewbot
[![Deploy](https://github.com/beerpiss/chuninewbot/actions/workflows/deploy.yaml/badge.svg)](https://github.com/beerpiss/chuninewbot/actions/workflows/deploy.yaml) [![State-of-the-art Shitcode](https://img.shields.io/static/v1?label=State-of-the-art&message=Shitcode&color=7B5804)](https://github.com/trekhleb/state-of-the-art-shitcode) [![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Discord bot for CHUNITHM International version.

### Features
- [x] Player data
- [x] Recent scores (including detailed judgements)
- [x] Best scores
  - [x] b30 and recent 10
  - [x] by song
- [x] Comparing scores
- [x] Song information
  - [x] sdvx.in integration
- [x] Search tracks by internal level
- [x] Calculate play rating
- [x] Slash command support
- [x] Minigames (song quiz)

### Setup instructions
0. Install Python 3.10 or newer and [Poetry](https://python-poetry.org/docs/#installation)
1. Copy `bot.example.ini` to `bot.ini` and fill in values based on the comments.
2. `poetry install` and `poetry shell`
3. Run `python dbutils.py create` to create the database.
4. Run `python dbutils.py update chunirec` to populate the song database. For this to work, `credentials.chunirec_token`
**must** be set in `bot.ini`. A pre-populated database is also provided [here](https://nightly.link/beerpiss/chuninewbot/workflows/test_creating_db.yaml/trunk/database.zip), for your convenience.
5. `python bot.py`

### Credits
Thanks to these projects for making this bot possible and less miserable to make:
- [Chunirec DB](https://db.chunirec.net) from [chunirec](https://twitter.com/chunirec)
- [arcade-songs](https://arcade-songs.zetaraku.dev) from [Raku Zeta](https://github.com/zetaraku)
- [CHUNITHM song alias list](https://github.com/lomotos10/GCM-bot/blob/main/data/aliases/en/chuni.tsv) from [lomotos10](https://github.com/lomotos10)

Thanks to all the [contributors](https://github.com/beerpiss/chuninewbot/graphs/contributors) who took part.
