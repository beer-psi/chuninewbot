import io.gitlab.arturbosch.detekt.Detekt

val libs: VersionCatalog = versionCatalogs.named("libs")

plugins {
    // Apply the org.jetbrains.kotlin.jvm Plugin to add support for Kotlin.
    kotlin("jvm")
    kotlin("plugin.serialization")
    id("io.gitlab.arturbosch.detekt")
}

group = "nadinenathaniel"
version = "unspecified"

repositories {
    // Use Maven Central for resolving dependencies.
    mavenCentral()
    google()
    maven(url = "https://jitpack.io")
    maven(url = "https://oss.sonatype.org/content/repositories/snapshots")
    maven(url = "https://s01.oss.sonatype.org/content/repositories/snapshots")
}

dependencies {
    testImplementation(libs.findBundle("test").get())
    detektPlugins(libs.findLibrary("detekt-rules-formatting").get())
}

tasks.test {
    useJUnitPlatform()
}

kotlin {
    jvmToolchain(17)
}

// Apply a specific Java toolchain to ease working on different environments.
java {
    toolchain {
        languageVersion.set(JavaLanguageVersion.of(17))
    }
}

detekt {
    buildUponDefaultConfig = true
    parallel = true
    autoCorrect = false
    ignoreFailures = false
    config.setFrom(files("$rootDir/config/detekt/detekt.yml"))
}

tasks.withType<Detekt>().configureEach {
    include("**/*.kt")
    exclude("**/resources/**", "**/build/**", "**/generated/**", "**/*.kts")
    reports {
        html.required.set(true)
        xml.required.set(false)
        txt.required.set(false)
    }
}
