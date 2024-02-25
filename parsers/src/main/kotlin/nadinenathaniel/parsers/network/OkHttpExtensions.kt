package nadinenathaniel.parsers.network

import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.suspendCancellableCoroutine
import okhttp3.Call
import okhttp3.Callback
import okhttp3.Response
import java.io.IOException
import kotlin.coroutines.resumeWithException

@OptIn(ExperimentalCoroutinesApi::class)
private suspend fun Call.await(callStack: Array<StackTraceElement>): Response = suspendCancellableCoroutine { cont ->
    val callback = object : Callback {
        override fun onResponse(call: Call, response: Response) {
            cont.resume(response) { response.body?.close() }
        }

        override fun onFailure(call: Call, e: IOException) {
            if (cont.isCancelled) {
                return
            }

            val exception = e.apply { stackTrace = callStack }

            cont.resumeWithException(exception)
        }
    }

    enqueue(callback)

    cont.invokeOnCancellation {
        try {
            cancel()
        } catch (_: Throwable) {}
    }
}

// We're not throwing anything, we are just taking the stack trace from
// the exception.
@Suppress("ThrowingExceptionsWithoutMessageOrCause")
suspend fun Call.await(): Response {
    val callStack = Exception().stackTrace.run { copyOfRange(1, size) }

    return await(callStack)
}

// We're not throwing anything, we are just taking the stack trace from
// the exception.
@Suppress("ThrowingExceptionsWithoutMessageOrCause")
suspend fun Call.awaitSuccess(): Response {
    val callStack = Exception().stackTrace.run { copyOfRange(1, size) }
    val response = await(callStack)

    if (!response.isSuccessful) {
        response.close()

        throw HttpException(response.code).apply { stackTrace = callStack }
    }

    return response
}

class HttpException(val code: Int) : IllegalStateException("HTTP error $code")
