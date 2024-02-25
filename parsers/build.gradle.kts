plugins {
    id("nadinenathaniel.kotlin-library-conventions")
}

dependencies {
    implementation(libs.okhttp)
    implementation(libs.jsoup)
    implementation(libs.kotlinx.coroutines.core)

    implementation(libs.korlibs.korim)

    testImplementation(libs.kotlinx.coroutines.test)
    testImplementation(libs.mockwebserver)
}
