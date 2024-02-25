package nadinenathaniel.kord.extensions.pagination

import com.kotlindiscord.kord.extensions.ExtensibleBot
import com.kotlindiscord.kord.extensions.i18n.TranslationsProvider
import com.kotlindiscord.kord.extensions.koin.KordExKoinComponent
import com.kotlindiscord.kord.extensions.pagination.EXPAND_EMOJI
import com.kotlindiscord.kord.extensions.pagination.SWITCH_EMOJI
import dev.kord.core.Kord
import dev.kord.core.behavior.UserBehavior
import dev.kord.core.entity.ReactionEmoji
import dev.kord.rest.builder.message.MessageBuilder
import io.github.oshai.kotlinlogging.KotlinLogging
import nadinenathaniel.kord.extensions.pagination.builders.PageTransitionCallback
import nadinenathaniel.kord.extensions.pagination.pages.Page
import nadinenathaniel.kord.extensions.pagination.pages.Pages
import org.koin.core.component.inject
import java.util.Locale

abstract class BasePaginator(
    val pages: Pages,
    open val owner: UserBehavior? = null,
    open val timeoutSeconds: Long? = null,
    open val keepEmbed: Boolean = true,
    open val switchEmoji: ReactionEmoji = if (pages.groups.size == 2) EXPAND_EMOJI else SWITCH_EMOJI,
    open val mutator: PageTransitionCallback? = null,
    open val bundle: String? = null,

    locale: Locale? = null
) : KordExKoinComponent {

    private val logger = KotlinLogging.logger {}

    /** Current instance of the bot. **/
    val bot: ExtensibleBot by inject()

    /** Kord instance, backing the ExtensibleBot. **/
    val kord: Kord by inject()

    /** Current translations provider. **/
    val translations: TranslationsProvider by inject()

    /** Locale to use for translations. **/
    open val localeObj: Locale = locale ?: bot.settings.i18nBuilder.defaultLocale

    /** What to do after the paginator times out. **/
    val timeoutCallbacks: MutableList<suspend () -> Unit> = mutableListOf()

    /** Currently-displayed page index. **/
    var currentPageNum: Int = 0

    /** Currently-displayed page group. **/
    var currentGroup: String = pages.defaultGroup

    /** Whether this paginator is currently active and processing events. **/
    open var active: Boolean = true

    /** Set of all page groups. **/
    open var allGroups: List<String> = pages.groups.map { it.key }

    init {
        if (pages.groups.filterValues { it.isNotEmpty() }.isEmpty()) {
            error("Attempted to send a paginator with no pages in it")
        }
    }

    /** Currently-displayed page object. **/
    open var currentPage: Page = pages.get(currentGroup, currentPageNum)

    /** Builder that generates an embed for the paginator's current context. **/
    open suspend fun MessageBuilder.applyPage() {
        val groupEmoji = if (pages.groups.size > 1) {
            currentGroup
        } else {
            null
        }

        currentPage.build(
            localeObj,
            currentPageNum,
            pages.groups[currentGroup]!!.size,
            groupEmoji,
            allGroups.indexOf(currentGroup),
            allGroups.size,
            mutator?.pageMutator
        )()

        mutator?.paginatorMutator?.let {
            it(this@BasePaginator)
        }
    }

    /** Send the paginator, given the current context. If it's already sent, update it. **/
    abstract suspend fun send()

    /** Should be called as part of [send] in order to create buttons and get other things set up. **/
    abstract suspend fun setup()

    /** Switch to the next group. Should not call [send]. **/
    abstract suspend fun nextGroup()

    /** Switch to a specific page. Should not call [send]. **/
    abstract suspend fun goToPage(page: Int)

    /** Destroy this paginator, removing its buttons and deleting its message if required.. **/
    abstract suspend fun destroy()

    /** Convenience function to go to call [goToPage] with the next page number, if we're not at the last page. **/
    open suspend fun nextPage() {
        if (currentPageNum < pages.groups[currentGroup]!!.size - 1) {
            goToPage(currentPageNum + 1)
        }
    }

    /** Convenience function to go to call [goToPage] with the previous page number, if we're not at the first page. **/
    open suspend fun previousPage() {
        if (currentPageNum != 0) {
            goToPage(currentPageNum - 1)
        }
    }

    /**
     * Register a callback that is called after the paginator times out.
     *
     * If there is no [timeoutSeconds] value set, your callbacks will never be called!
     */
    open fun onTimeout(body: suspend () -> Unit): BasePaginator {
        timeoutCallbacks.add(body)

        return this
    }

    /** @suppress Call the timeout callbacks. **/
    @Suppress("TooGenericExceptionCaught")  // Come on, now.
    open suspend fun runTimeoutCallbacks() {
        timeoutCallbacks.forEach {
            try {
                it.invoke()
            } catch (t: Throwable) {
                logger.error(t) { "Error thrown by timeout callback: $it" }
            }
        }
    }

    /** Quick access to translations, using the paginator's locale and bundle. **/
    fun translate(key: String, replacements: Array<Any?> = arrayOf()): String =
        translations.translate(key, localeObj, bundle, replacements = replacements)
}
