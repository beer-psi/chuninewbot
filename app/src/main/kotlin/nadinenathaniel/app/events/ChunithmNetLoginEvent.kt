package nadinenathaniel.app.events

import com.kotlindiscord.kord.extensions.events.KordExEvent
import nadinenathaniel.app.network.NetscapeCookieJar
import nadinenathaniel.parsers.chunithm.model.profile.ChunithmPlayerProfile

class ChunithmNetLoginEvent(
    val otp: String,
    val profile: ChunithmPlayerProfile,
    val cookieJar: NetscapeCookieJar,
) : KordExEvent
