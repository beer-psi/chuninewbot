package nadinenathaniel.kord.extensions.message.builders

import dev.kord.common.entity.DiscordMessageReference
import dev.kord.common.entity.InteractionResponseType
import dev.kord.common.entity.MessageFlag
import dev.kord.common.entity.MessageFlags
import dev.kord.common.entity.Permission.ReadMessageHistory
import dev.kord.common.entity.Snowflake
import dev.kord.common.entity.optional.Optional
import dev.kord.common.entity.optional.OptionalBoolean
import dev.kord.common.entity.optional.OptionalSnowflake
import dev.kord.common.entity.optional.delegate.delegate
import dev.kord.common.entity.optional.map
import dev.kord.common.entity.optional.mapCopy
import dev.kord.common.entity.optional.mapList
import dev.kord.common.entity.optional.optional
import dev.kord.rest.NamedFile
import dev.kord.rest.builder.component.MessageComponentBuilder
import dev.kord.rest.builder.message.AllowedMentionsBuilder
import dev.kord.rest.builder.message.AttachmentBuilder
import dev.kord.rest.builder.message.EmbedBuilder
import dev.kord.rest.builder.message.MessageBuilder
import dev.kord.rest.json.request.FollowupMessageCreateRequest
import dev.kord.rest.json.request.InteractionApplicationCommandCallbackData
import dev.kord.rest.json.request.InteractionResponseCreateRequest
import dev.kord.rest.json.request.MessageCreateRequest
import dev.kord.rest.json.request.MultipartFollowupMessageCreateRequest
import dev.kord.rest.json.request.MultipartInteractionResponseCreateRequest
import dev.kord.rest.json.request.MultipartMessageCreateRequest

class HybridMessageCreateBuilder(private val ephemeral: Boolean) : MessageBuilder {

    private var _nonce: Optional<String> = Optional.Missing()

    /** A value that can be used to verify a message was sent (up to 25 characters). */
    var nonce: String? by ::_nonce.delegate()

    private var _messageReference: OptionalSnowflake = OptionalSnowflake.Missing

    /**
     * The id of the message being replied to.
     *
     * Requires the [ReadMessageHistory] permission.
     *
     * Replying will not mention the author by default, set [AllowedMentionsBuilder.repliedUser] to `true` via
     * [allowedMentions] to mention the author.
     */
    var messageReference: Snowflake? by ::_messageReference.delegate()

    private var _failIfNotExists: OptionalBoolean = OptionalBoolean.Missing

    private var _stickerIds: Optional<MutableList<Snowflake>> = Optional.Missing()

    /** The IDs of up to three stickers to send in the message. */
    var stickerIds: MutableList<Snowflake>? by ::_stickerIds.delegate()

    private var _content: Optional<String> = Optional.Missing()
    override var content: String? by ::_content.delegate()

    private var _tts: OptionalBoolean = OptionalBoolean.Missing
    var tts: Boolean? by ::_tts.delegate()

    private var _embeds: Optional<MutableList<EmbedBuilder>> = Optional.Missing()
    override var embeds: MutableList<EmbedBuilder>? by ::_embeds.delegate()

    private var _allowedMentions: Optional<AllowedMentionsBuilder> = Optional.Missing()
    override var allowedMentions: AllowedMentionsBuilder? by ::_allowedMentions.delegate()

    private var _components: Optional<MutableList<MessageComponentBuilder>> = Optional.Missing()
    override var components: MutableList<MessageComponentBuilder>? by ::_components.delegate()

    override val files: MutableList<NamedFile> = mutableListOf()

    private var _attachments: Optional<MutableList<AttachmentBuilder>> = Optional.Missing()
    override var attachments: MutableList<AttachmentBuilder>? by ::_attachments.delegate()

    override var flags: MessageFlags? = null
    override var suppressEmbeds: Boolean? = null
    var suppressNotifications: Boolean? = null

    fun toFollowupRequest() = MultipartFollowupMessageCreateRequest(
        FollowupMessageCreateRequest(
            content = _content,
            tts = _tts,
            embeds = _embeds.mapList { it.toRequest() },
            allowedMentions = _allowedMentions.map { it.build() },
            components = _components.mapList { it.build() },
            attachments = _attachments.mapList { it.toRequest() },
            flags = buildMessageFlags(flags, suppressEmbeds, suppressNotifications, ephemeral),
        ),
        files,
    )

    fun toResponseRequest() = MultipartInteractionResponseCreateRequest(
        InteractionResponseCreateRequest(
            type = InteractionResponseType.ChannelMessageWithSource,
            data = InteractionApplicationCommandCallbackData(
                tts = _tts,
                content = _content,
                embeds = _embeds.mapList { it.toRequest() },
                allowedMentions = _allowedMentions.map { it.build() },
                flags = buildMessageFlags(flags, suppressEmbeds, suppressNotifications, ephemeral),
                components = _components.mapList { it.build() },
                attachments = _attachments.mapList { it.toRequest() },
            ).optional(),
        ),
        files,
    )

    fun toChatRequest() = MultipartMessageCreateRequest(
        MessageCreateRequest(
            content = _content,
            nonce = _nonce,
            tts = _tts,
            embeds = _embeds.mapList { it.toRequest() },
            allowedMentions = _allowedMentions.map { it.build() },
            messageReference = when (val id = _messageReference) {
                is OptionalSnowflake.Value ->
                    Optional.Value(DiscordMessageReference(id = id, failIfNotExists = _failIfNotExists))
                is OptionalSnowflake.Missing -> Optional.Missing()
            },
            components = _components.mapList { it.build() },
            stickerIds = _stickerIds.mapCopy(),
            attachments = _attachments.mapList { it.toRequest() },
            flags = buildMessageFlags(flags, suppressEmbeds, suppressNotifications)
        ),
        files,
    )
}

fun buildMessageFlags(
    base: MessageFlags?,
    suppressEmbeds: Boolean?,
    suppressNotifications: Boolean? = null,
    ephemeral: Boolean? = null,
): Optional<MessageFlags> =
    if (base == null && suppressEmbeds == null && suppressNotifications == null && ephemeral == null) {
        Optional.Missing()
    } else {
        val flags = MessageFlags {
            if (base != null) +base
            fun apply(add: Boolean?, flag: MessageFlag) = when (add) {
                true -> +flag
                false -> -flag
                null -> {}
            }
            apply(suppressEmbeds, MessageFlag.SuppressEmbeds)
            apply(suppressNotifications, MessageFlag.SuppressNotifications)
            apply(ephemeral, MessageFlag.Ephemeral)
        }
        Optional.Value(flags)
    }
