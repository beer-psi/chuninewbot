@file:Suppress("MagicNumber")
package nadinenathaniel.parsers.chunithm.util

import korlibs.image.bitmap.NativeImageContext2d
import korlibs.image.format.PNG
import korlibs.image.format.encode
import korlibs.image.format.readNativeImage
import korlibs.io.async.async
import korlibs.io.stream.toAsync
import korlibs.math.geom.Angle
import korlibs.math.geom.Point
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.awaitAll
import nadinenathaniel.parsers.chunithm.model.profile.ChunithmPlayerAvatar
import nadinenathaniel.parsers.network.awaitSuccess
import okhttp3.OkHttpClient
import okhttp3.Request

internal suspend fun renderPlayerAvatarInternal(
    client: OkHttpClient,
    avatar: ChunithmPlayerAvatar,
    dispatcher: CoroutineDispatcher = Dispatchers.IO,
): ByteArray {
    val avatarImages = avatar.asMap().map {
        async(dispatcher) {
            val request = Request.Builder()
                .method("GET", null)
                .url(it.value)
                .build()
            val response = client.newCall(request).awaitSuccess()

            it.key to response.body!!.byteStream()
                .toAsync()
                .readNativeImage()
        }
    }
        .awaitAll()
        .toMap()
    val base = avatarImages["base"]!!

    return NativeImageContext2d(base.width, base.height - 20) {
        drawImage(base, Point(0, -20))

        val back = avatarImages["back"]!!
        val baseX = (this.width - back.width) / 2

        drawImage(back, Point(baseX, 5))

        avatarCoords.entries.forEach {
            val coords = it.value
            val cropped = NativeImageContext2d(coords.width, coords.height) {
                rotate(Angle.fromDegrees(coords.rotate))
                drawImage(
                    avatarImages[it.key]!!,
                    Point(-coords.sx, -coords.sy),
                )
            }


            drawImage(
                cropped,
                Point(baseX + coords.dxOffset, coords.dy),
            )
        }
    }
        .encode(PNG)
}

private val avatarCoords by lazy {
    mapOf(
        "skinFootR" to DrawCoordinates(0, 204, 84, 260, 42, 52, 0),
        "skinFootL" to DrawCoordinates(42, 204, 147, 260, 42, 52, 0),
        "skin" to DrawCoordinates(0, 0, 72, 73, 128, 204, 0),
        "wear" to DrawCoordinates(0, 0, 7, 86, 258, 218, 0),
        "face" to DrawCoordinates(0, 0, 107, 80, 58, 64, 0),
        "faceCover" to DrawCoordinates(0, 0, 78, 76, 116, 104, 0),
        "head" to DrawCoordinates(0, 0, 37, 8, 200, 150, 0),
        "handR" to DrawCoordinates(0, 0, 52, 158, 36, 72, 0),
        "handL" to DrawCoordinates(0, 0, 184, 158, 36, 72, 0),
        "itemR" to DrawCoordinates(0, 0, -3, 35, 100, 272, -5),
        "itemL" to DrawCoordinates(100, 0, 175, 25, 100, 272, 5),
    )
}

private class DrawCoordinates(
    val sx: Int,
    val sy: Int,
    val dxOffset: Int,
    val dy: Int,
    val width: Int,
    val height: Int,
    val rotate: Int,
)
