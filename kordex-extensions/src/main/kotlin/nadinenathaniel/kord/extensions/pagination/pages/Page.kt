package nadinenathaniel.kord.extensions.pagination.pages

import com.kotlindiscord.kord.extensions.i18n.TranslationsProvider
import com.kotlindiscord.kord.extensions.koin.KordExKoinComponent
import com.kotlindiscord.kord.extensions.utils.capitalizeWords
import com.kotlindiscord.kord.extensions.utils.textOrNull
import dev.kord.rest.builder.message.EmbedBuilder
import dev.kord.rest.builder.message.MessageBuilder
import dev.kord.rest.builder.message.embed
import nadinenathaniel.kord.extensions.pagination.builders.PageMutator
import org.koin.core.component.inject
import java.util.Locale

class Page(
    private val bundle: String? = null,
    private val paginationInformationOnLastEmbed: Boolean = false,
    val builder: suspend MessageBuilder.() -> Unit,
) : KordExKoinComponent {

    private val translationsProvider: TranslationsProvider by inject()

    suspend fun build(
        locale: Locale,
        pageNum: Int,
        pages: Int,
        group: String?,
        groupIndex: Int,
        groups: Int,
        mutator: PageMutator? = null,
    ): suspend MessageBuilder.() -> Unit = {
        builder()

        if (mutator != null) {
            mutator(this, this@Page)
        }

        val lastEmbed = embeds?.lastOrNull()

        if (lastEmbed != null && paginationInformationOnLastEmbed) {
            lastEmbed.apply { addPaginationInformation(locale, pageNum, pages, group, groupIndex, groups) }
        } else {
            embed { addPaginationInformation(locale, pageNum, pages, group, groupIndex, groups) }
        }
    }

    private suspend fun EmbedBuilder.addPaginationInformation(
        locale: Locale,
        pageNum: Int,
        pages: Int,
        group: String?,
        groupIndex: Int,
        groups: Int,
    ) {
        val curFooterText = footer?.textOrNull()
        val curFooterIcon = footer?.icon

        footer {
            icon = curFooterIcon

            text = buildString {
                if (pages > 1) {
                    append(
                        translationsProvider.translate(
                            "paginator.footer.page",
                            locale,
                            replacements = arrayOf(pageNum + 1, pages)
                        )
                    )
                }

                if (!group.isNullOrBlank() || groups > 2) {
                    if (isNotBlank()) {
                        append(" • ")
                    }

                    if (group.isNullOrBlank()) {
                        append(
                            translationsProvider.translate(
                                "paginator.footer.group",
                                locale,
                                replacements = arrayOf(groupIndex + 1, groups)
                            )
                        )
                    } else {
                        val groupName = translationsProvider.translate(
                            group, locale, bundle
                        ).capitalizeWords(locale)

                        append("$groupName (${groupIndex + 1}/$groups)")
                    }
                }

                if (!curFooterText.isNullOrEmpty()) {
                    if (isNotBlank()) {
                        append(" • ")
                    }

                    append(curFooterText)
                }
            }
        }
    }
}
