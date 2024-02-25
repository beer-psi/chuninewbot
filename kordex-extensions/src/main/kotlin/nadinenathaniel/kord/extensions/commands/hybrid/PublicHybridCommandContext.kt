package nadinenathaniel.kord.extensions.commands.hybrid

import com.kotlindiscord.kord.extensions.commands.Arguments
import com.kotlindiscord.kord.extensions.commands.CommandContext
import nadinenathaniel.kord.extensions.entity.PublicHybridMessage
import nadinenathaniel.kord.extensions.message.builders.HybridMessageCreateBuilder
import kotlin.contracts.ExperimentalContracts
import kotlin.contracts.InvocationKind
import kotlin.contracts.contract

class PublicHybridCommandContext<T: Arguments>(
    context: CommandContext,
) {

    @OptIn(ExperimentalContracts::class)
    suspend inline fun respond(
        builder: HybridMessageCreateBuilder.() -> Unit,
    ): PublicHybridMessage {
        contract { callsInPlace(builder, InvocationKind.EXACTLY_ONCE) }

        val builder = HybridMessageCreateBuilder(false).apply(builder)

        TODO()
    }
}
