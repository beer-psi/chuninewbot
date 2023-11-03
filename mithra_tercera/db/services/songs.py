import asyncio
import itertools
from typing import Optional, TypedDict, Sequence, Literal, cast

from fuzzywuzzy import fuzz, process

from mithra_tercera.db.models import Song


Term = tuple[int, str | None]


class SearchData(TypedDict):
    id: int
    title: str
    artist: str
    search_terms__guild_id: Optional[int]
    search_terms__alias: Optional[str]


class SongService:
    @staticmethod
    async def search_song_by_title(
        query: str,
        *,
        score_cutoff: int = 50,
        guild_id: Optional[int] = None,
        fetch_related: bool = True,
    ) -> Optional[Song]:
        """
        Returns the song that best matches a query, or None if there are no satisfactory matches.

        :param query: The search query.
        :param score_cutoff: Minimum score for a song to be considered a match.
        :param guild_id:
            ID of the guild (Discord server) that triggered this search query. Used to search for guild-specific
            aliases.
        :param fetch_related: Fetch charts and chart views if there was a result.
        """

        def search(
            data: Sequence[SearchData],
            control: Literal["title", "artist", "search_terms__alias"],
            query: str,
            guild_id: Optional[int],
            *,
            score_cutoff: int = 60,
        ) -> list[tuple[int, int]]:
            if control == "search_terms__alias":
                terms: list[Term] = [
                    (x["id"], x["search_terms__alias"])
                    for x in data
                    if x["search_terms__guild_id"] == -1
                    or x["search_terms__guild_id"] == guild_id
                ]
            else:
                terms: list[Term] = [(x["id"], x[control]) for x in data]

            # limit=None is okay, whoever did the type stubs suck
            results: list[tuple[Term, int]] = process.extractBests(
                query,
                terms,
                score_cutoff=score_cutoff,
                scorer=fuzz.QRatio,
                limit=None,  # type: ignore[reportGeneralTypeIssues]
            )

            # song ID and its score
            return [(x[0][0], x[1]) for x in results]

        data = cast(
            Sequence[SearchData],
            await Song.all().values(
                "id", "title", "artist", "search_terms__guild_id", "search_terms__alias"
            ),
        )

        tasks = [
            asyncio.to_thread(
                search, data, control, query, guild_id, score_cutoff=score_cutoff
            )
            for control in ("title", "artist", "search_terms__alias")
        ]
        results = itertools.chain.from_iterable(await asyncio.gather(*tasks))

        try:
            song_id, _ = max(results, key=lambda x: x[1])
        except ValueError:
            # Thrown if results is empty.
            return None

        song = await Song.get(id=song_id)
        if fetch_related:
            await song.fetch_related("charts", "charts__sdvxin")

        return song
