from typing import Optional

from jarowinkler import jarowinkler_similarity
from sqlalchemy import (
    ColumnElement,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
    type_coerce,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from utils import sdvxin_link


class Base(DeclarativeBase, AsyncAttrs):
    pass


class Cookie(Base):
    __tablename__ = "cookies"

    discord_id: Mapped[int] = mapped_column(primary_key=True)
    cookie: Mapped[str] = mapped_column(String(64), nullable=False)


class Song(Base):
    __tablename__ = "chunirec_songs"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    chunithm_id: Mapped[int] = mapped_column(nullable=False)

    title: Mapped[str] = mapped_column(nullable=False)

    chunithm_catcode: Mapped[int] = mapped_column(nullable=False)
    genre: Mapped[str] = mapped_column(nullable=False)
    artist: Mapped[str] = mapped_column(nullable=False)
    release: Mapped[str] = mapped_column(nullable=False)
    bpm: Mapped[int] = mapped_column(nullable=False)

    jacket: Mapped[str] = mapped_column(nullable=False)
    zetaraku_jacket: Mapped[str] = mapped_column(nullable=False)

    charts: Mapped[list["Chart"]] = relationship(
        back_populates="song", cascade="all, delete-orphan"
    )
    aliases: Mapped[list["Alias"]] = relationship(
        back_populates="song", cascade="all, delete-orphan"
    )

    @hybrid_method
    def similarity(self, search: str) -> float:
        return jarowinkler_similarity(self.title.lower(), search.lower())

    @similarity.inplace.expression
    @classmethod
    def _similarity_expr(cls, search: str) -> ColumnElement[float]:
        return type_coerce(func.jwsim(func.lower(cls.title), search.lower()), Float)


class Chart(Base):
    __tablename__ = "chunirec_charts"
    __table_args__ = (
        UniqueConstraint("song_id", "difficulty", name="_song_id_difficulty_uc"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    song_id: Mapped[str] = mapped_column(
        ForeignKey("chunirec_songs.id"), nullable=False
    )

    difficulty: Mapped[str] = mapped_column(nullable=False)
    level: Mapped[float] = mapped_column(nullable=False)
    const: Mapped[float] = mapped_column(nullable=False)

    maxcombo: Mapped[int] = mapped_column(nullable=False)
    is_const_unknown: Mapped[bool] = mapped_column(nullable=False)

    song: Mapped["Song"] = relationship(back_populates="charts")
    sdvxin_chart_view: Mapped[Optional["SdvxinChartView"]] = relationship(
        back_populates="chunithm_chart",
        primaryjoin="and_(Chart.song_id == SdvxinChartView.song_id, Chart.difficulty == SdvxinChartView.difficulty)",
    )


class Alias(Base):
    __tablename__ = "aliases"
    __table_args__ = (UniqueConstraint("alias", "guild_id", name="_alias_guild_id_uc"),)

    rowid: Mapped[int] = mapped_column(primary_key=True)

    alias: Mapped[str] = mapped_column(nullable=False)
    guild_id: Mapped[int] = mapped_column(nullable=False)
    song_id: Mapped[str] = mapped_column(
        ForeignKey("chunirec_songs.id"), nullable=False
    )

    song: Mapped["Song"] = relationship(back_populates="aliases")

    @hybrid_method
    def similarity(self, search: str) -> float:
        return jarowinkler_similarity(self.alias.lower(), search.lower())

    @similarity.inplace.expression
    @classmethod
    def _similarity_expr(cls, search: str) -> ColumnElement[float]:
        return type_coerce(func.jwsim(func.lower(cls.alias), search.lower()), Float)


class Prefix(Base):
    __tablename__ = "guild_prefix"

    guild_id: Mapped[int] = mapped_column(primary_key=True)
    prefix: Mapped[str] = mapped_column(nullable=False)


class SdvxinChartView(Base):
    __tablename__ = "sdvxin"
    __table_args__ = (UniqueConstraint("id", "difficulty", name="_id_difficulty_uc"),)

    rowid: Mapped[int] = mapped_column(primary_key=True)

    id: Mapped[str] = mapped_column(nullable=False)
    song_id: Mapped[str] = mapped_column(
        ForeignKey("chunirec_charts.song_id"), nullable=False
    )
    difficulty: Mapped[str] = mapped_column(
        ForeignKey("chunirec_charts.difficulty"), nullable=False
    )

    chunithm_chart: Mapped["Chart"] = relationship(
        back_populates="sdvxin_chart_view",
        primaryjoin="and_(Chart.song_id == SdvxinChartView.song_id, Chart.difficulty == SdvxinChartView.difficulty)",
    )

    @hybrid_property
    def url(self) -> str:
        return sdvxin_link(self.id, self.difficulty)


class GuessScore(Base):
    __tablename__ = "guess_leaderboard"

    discord_id: Mapped[int] = mapped_column(primary_key=True)
    score: Mapped[int] = mapped_column(nullable=False)
