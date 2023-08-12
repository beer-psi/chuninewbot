## chuninewbot
[![State-of-the-art Shitcode](https://img.shields.io/static/v1?label=State-of-the-art&message=Shitcode&color=7B5804)](https://github.com/trekhleb/state-of-the-art-shitcode)

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
1. Copy `.env.example` to `.env` and fill in:
- `TOKEN` with the bot's token
- `CHUNIREC_TOKEN` with a token obtained from [Chunirec Developer Portal](https://developer.chunirec.net/)
- `LOGIN_ENDPOINT_PORT` with an unprivileged, available port (>1024). This will be used by the web server to handle logins.
Set to `-1` to disable.
2. `poetry install`
3. Run `update_db.py` to populate the song database. For your convenience, a pre-populated database is also provided [here](https://cdn.discordapp.com/attachments/1041530799704526961/1139868803359060088/database.sqlite3).
4. `python bot.py`

### Credits
Thanks to these projects for making this bot possible and less miserable to make:
- [chunirec](https://twitter.com/chunirec) for the wonderful [Chunirec DB](https://db.chunirec.net), which is the bot's primary data source
- [lomotos10](https://github.com/lomotos10) for [CHUNITHM's song alias list](https://github.com/lomotos10/GCM-bot/blob/main/data/aliases/en/chuni.tsv)



