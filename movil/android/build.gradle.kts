allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}
subprojects {
    project.evaluationDependsOn(":app")
}
subprojects {
    // CameraX 1.5 necesita androidx.concurrent-futures en el classpath de
    // compilación del plugin de cámara para resolver sus anotaciones de tipo.
    if (name == "camera_android_camerax") {
        fun addFutures(): Unit = dependencies {
            add("implementation", "androidx.concurrent:concurrent-futures:1.2.0")
        }
        if (plugins.hasPlugin("com.android.library")) {
            addFutures()
        } else {
            plugins.withId("com.android.library") {
                addFutures()
            }
        }
    }
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
