# Dealing with a relational database over here.
# ruff: noqa: A003
import re
from typing import Literal, Self
from urllib.parse import quote

from tortoise import fields
from tortoise.fields import Field
from tortoise.fields.relational import ForeignKeyRelation, ReverseRelation
from tortoise.models import Model
from tortoise.validators import RegexValidator


class Cookie(Model):
    user_id = fields.BigIntField(pk=True, generated=False, null=False)
    cookie = fields.CharField(64, null=False)
    kamaitachi_token = fields.CharField(40, null=False)


class GuessScore(Model):
    user_id = fields.BigIntField(pk=True, generated=False, null=False)
    score = fields.IntField(null=False)


class Song(Model):
    id = fields.IntField(pk=True, null=False, generated=False)

    title = fields.TextField(null=False)
    artist = fields.TextField(null=False)

    displayed_version = fields.TextField(null=True)
    catcode = fields.IntField(null=True)

    # Technically, there are songs like Nhelv, with a BPM of 174.59,
    # but CHUNITHM displays 175BPM. If SEGA doesn't care, why should we?
    bpm = fields.IntField(null=True)

    jacket = fields.TextField(null=True)

    charts: ReverseRelation["Chart"]
    search_terms: ReverseRelation["SearchTerm"]

    def __repr__(self: Self) -> str:
        return f"Song(id={self.id}, title={self.title}, artist={self.artist})"

    @property
    def genre(self: Self) -> str:
        return ["POPS&ANIME", "", "niconico", "東方Project", "", "ORIGINAL", "VARIETY", "イロドリミドリ", "", "ゲキマイ"][self.catcode]


class Chart(Model):
    id = fields.IntField(pk=True)

    song: ForeignKeyRelation[Song] = fields.ForeignKeyField(
        "models.Song", related_name="charts", on_delete=fields.CASCADE, null=False
    )

    charter = fields.TextField(null=True)

    # This is fine.
    difficulty: Field[Literal["BAS", "ADV", "MAS", "EXP", "ULT", "WE"]] = fields.CharField(
        max_length=3,
        null=False,
        validators=[RegexValidator(r"BAS|ADV|EXP|MAS|ULT|WE", re.UNICODE)],
    )  # type: ignore[reportGeneralTypeIssues]
    level = fields.CharField(max_length=3, null=False)
    const = fields.FloatField(null=True)

    maxcombo = fields.IntField(null=True)
    tap = fields.IntField(null=True)
    hold = fields.IntField(null=True)
    slide = fields.IntField(null=True)
    air = fields.IntField(null=True)
    flick = fields.IntField(null=True)

    sdvxin: ReverseRelation["SdvxinChartView"]

    class Meta:
        unique_together = (("song", "difficulty"),)


class SearchTerm(Model):
    id = fields.IntField(pk=True)

    alias = fields.TextField(null=False)
    owner_id = fields.BigIntField(null=True)

    # HACK: Set to -1 for global aliases.
    # SQLite isn't exactly happy when nullable columns get used in a unique
    # constraint.
    guild_id = fields.BigIntField(null=False, default=-1)

    song: ForeignKeyRelation[Song] = fields.ForeignKeyField(
        "models.Song", related_name="search_terms", on_delete=fields.CASCADE, null=False
    )

    class Meta:
        unique_together = (("alias", "guild_id"),)


class Prefix(Model):
    guild_id = fields.BigIntField(pk=True, generated=False, null=False)
    prefix = fields.TextField(null=False)


class SdvxinChartView(Model):
    id = fields.CharField(10, pk=True, generated=False)
    end_index = fields.CharField(10, default="")
    chart: ForeignKeyRelation[Chart] = fields.ForeignKeyField(
        "models.Chart",
        related_name="sdvxin",
        on_delete=fields.CASCADE,
        null=False,
    )

    @property
    def url(self: Self) -> str:
        return f"https://sdvx.in/chunithm/{self.id[:2]}/{self.id}{self.chart.difficulty.lower()}{self.end_index}.htm"

    def __repr__(self: Self) -> str:
        return f"SdvxinChartView(id={self.id})"
