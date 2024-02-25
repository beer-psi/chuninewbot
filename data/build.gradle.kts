plugins {
    id("nadinenathaniel.kotlin-library-conventions")
    id("app.cash.sqldelight") version libs.versions.sqldelight
}

dependencies {
    implementation(libs.sqldelight.drivers.jdbc)
}

sqldelight {
    databases {
        create("Database") {
            packageName.set("nadinenathaniel.data")
            dialect(libs.sqldelight.dialects.postgres)
            schemaOutputDirectory.set(project.file("./src/main/sqldelight"))
            deriveSchemaFromMigrations.set(true)
        }
    }
}
