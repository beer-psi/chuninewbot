package nadinenathaniel.app.util

import nadinenathaniel.parsers.chunithm.model.score.ChunithmRecentScore

/**
 * Group a list of recent scores into credits. This assumes that the newest score is
 * always at the start of the list, and so the track order is `[4, 3, 2, 1]`.
 */
@Suppress("DoubleMutabilityForCollection")
fun List<ChunithmRecentScore>.groupByCredit(): List<List<ChunithmRecentScore>> = buildList {
    var subList = mutableListOf<ChunithmRecentScore>()

    for (score in this@groupByCredit) {
        subList.add(score)

        if (score.track == 1) {
            add(subList)
            subList = mutableListOf()
        }
    }
}
