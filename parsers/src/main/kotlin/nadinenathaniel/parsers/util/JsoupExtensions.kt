package nadinenathaniel.parsers.util

import okhttp3.Response
import org.jsoup.Jsoup
import org.jsoup.nodes.Document

internal fun Response.asJsoup(html: String? = null): Document {
    val baseUrl = request.url.toString()
    val body = html ?: body?.string() ?: return Document.createShell(baseUrl)

    return Jsoup.parse(body, baseUrl)
}
