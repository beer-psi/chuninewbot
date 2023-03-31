## chuninewbot
[![State-of-the-art Shitcode](https://img.shields.io/static/v1?label=State-of-the-art&message=Shitcode&color=7B5804)](https://github.com/trekhleb/state-of-the-art-shitcode)

Discord bot for CHUNITHM International version.

### Features
- [x] Player data
- [x] Recent scores (including detailed judgements)
- [ ] Best scores (b30, song)
- [x] Comparing scores
- [ ] Song information
- [x] Search tracks by internal level
- [x] Calculate play rating
- [ ] Slash command support
- [ ] Minigames (song quiz)

### Setup instructions
1. Copy `.env.example` to `.env` and fill in:
- `TOKEN` with the bot's token
- `CHUNIREC_TOKEN` with a token obtained from [Chunirec Developer Portal](https://developer.chunirec.net/)
2. `poetry install`
3. Run `update_db.py` to populate the song database
4. `python bot.py`


