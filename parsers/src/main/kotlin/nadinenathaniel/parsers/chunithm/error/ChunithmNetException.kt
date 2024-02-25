package nadinenathaniel.parsers.chunithm.error

import java.io.IOException

class ChunithmNetException(
    val code: Int,
    val errorMessage: String,
) : IOException("$errorMessage [$code]")
