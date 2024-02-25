package nadinenathaniel.kord.extensions.entity

import dev.kord.common.entity.Snowflake
import dev.kord.core.Kord
import dev.kord.core.behavior.channel.MessageChannelBehavior
import dev.kord.core.entity.KordEntity
import dev.kord.core.entity.Message
import dev.kord.core.entity.Strategizable
import dev.kord.core.entity.channel.MessageChannel
import dev.kord.core.entity.interaction.followup.PublicFollowupMessage
import dev.kord.core.supplier.EntitySupplier
import dev.kord.core.supplier.EntitySupplyStrategy
import dev.kord.core.supplier.getChannelOf
import dev.kord.core.supplier.getChannelOfOrNull
import kotlin.contracts.ExperimentalContracts

sealed class HybridMessage : KordEntity, Strategizable {

    abstract val applicationId: Snowflake?
    abstract val token: String?
    abstract val message: Message

    override val id: Snowflake get() = message.id
    val channelId: Snowflake get() = message.channelId

    val isInteraction: Boolean get() = applicationId != null && token != null
    val channel: MessageChannelBehavior get() = MessageChannelBehavior(channelId, kord)

    suspend fun getChannel(): MessageChannel = supplier.getChannelOf(channelId)

    suspend fun getChannelOfOrNull(): MessageChannel? = supplier.getChannelOfOrNull(channelId)
}

class PublicHybridMessage(
    override val message: Message,
    override val applicationId: Snowflake?,
    override val token: String?,
    override val kord: Kord,
    override val supplier: EntitySupplier = kord.defaultSupplier
): HybridMessage() {

//    @OptIn(ExperimentalContracts::class)
//    suspend inline fun edit(builder: HybridMessageModifyBuilder.() -> Unit): PublicHybridMessage {
//        contract { callsInPlace(builder, InvocationKind.EXACTLY_ONCE) }
//        val builder = HybridMessageModifyBuilder().apply(builder)
//
//        val response = if(isInteraction) {
//            kord.rest.interaction.modifyFollowupMessage(applicationId!!, token!!, id, builder.toFollowupRequest())
//        } else {
//            kord.rest.channel.editMessage(channelId, id, builder.toChatRequest())
//        }
//
//        return PublicHybridMessage(Message(response.toData(), kord), applicationId, token, kord)
//    }

    suspend fun delete() = if (isInteraction) {
        kord.rest.interaction.deleteFollowupMessage(applicationId!!, token!!, id)
    } else {
        kord.rest.channel.deleteMessage(channelId, id)
    }

    override fun withStrategy(strategy: EntitySupplyStrategy<*>): Strategizable = if (isInteraction) {
        PublicFollowupMessage(message, applicationId!!, token!!, kord, strategy.supply(kord))
    } else {
        Message(message.data, kord, strategy.supply(kord))
    }
}
