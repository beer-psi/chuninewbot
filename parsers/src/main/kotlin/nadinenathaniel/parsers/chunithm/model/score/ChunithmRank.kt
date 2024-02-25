package nadinenathaniel.parsers.chunithm.model.score

enum class ChunithmRank(val border: Int) {
    D(0),
    C(500_000),
    B(600_000),
    BB(700_000),
    BBB(800_000),
    A(900_000),
    AA(925_000),
    AAA(950_000),
    S(975_000),
    S_PLUS(990_000),
    SS(1_000_000),
    SS_PLUS(1_005_000),
    SSS(1_007_500),
    SSS_PLUS(1_009_000),
    ;

    override fun toString(): String = this.name.replace("_PLUS", "+")

    companion object {
        fun fromScore(score: Int): ChunithmRank {
            require(score in (0..MAX_SCORE)) {
                "Score is not in valid range."
            }

            return enumValues<ChunithmRank>().last { score >= it.border }
        }

        fun fromIndex(index: Int): ChunithmRank {
            return enumValues<ChunithmRank>()[index]
        }
    }
}

private const val MAX_SCORE = 1_010_000
