import Dependencies._

val hadoopVersion = "2.5.0-cdh5.3.1" // IA cluster 2018-05-21: 2.5.0-cdh5.3.1
val hbaseVersion = "0.98.6-cdh5.3.1" // IA cluster 2018-05-21: 0.98.6-cdh5.3.1

lazy val root = (project in file(".")).

  settings(
    inThisBuild(List(
      organization := "org.archive",
      scalaVersion := "2.11.8",
      version      := "0.1.0-SNAPSHOT",
      test in assembly := {},
    )),

    name := "scald-mvp",

    resolvers += "conjars.org" at "http://conjars.org/repo",
    resolvers += "Apache HBase" at "https://repository.apache.org/content/repositories/releases",
    resolvers += "Cloudera Maven Repository" at "https://repository.cloudera.com/artifactory/cloudera-repos",
    resolvers += "Twitter Maven Repository" at "https://maven.twttr.com",

    libraryDependencies += scalaTest % Test,
    libraryDependencies += "org.scala-lang" % "scala-library" % "2.11.8",
    libraryDependencies += "com.twitter" % "scalding-core_2.11" % "0.17.2",
    libraryDependencies += "org.apache.hadoop" % "hadoop-common" % hadoopVersion,
    libraryDependencies += "org.apache.hadoop" % "hadoop-client" % hadoopVersion,
    libraryDependencies += "org.apache.hadoop" % "hadoop-mapreduce-client-jobclient" % hadoopVersion classifier "tests",
    libraryDependencies += "org.apache.hbase" % "hbase-common" % hbaseVersion,
    libraryDependencies += "parallelai" % "parallelai.spyglass" % "2.11_0.17.2_cdh5.3.1",

    // cargo-culted from twitter/scalding's build.sbt
    // hint via https://stackoverflow.com/questions/23280494/sbt-assembly-error-deduplicate-different-file-contents-found-in-the-following#23280952
    mergeStrategy in assembly :=  {
        case s if s.endsWith(".class") => MergeStrategy.last
        case s if s.endsWith("project.clj") => MergeStrategy.concat
        case s if s.endsWith(".html") => MergeStrategy.last
        case s if s.endsWith(".dtd") => MergeStrategy.last
        case s if s.endsWith(".xsd") => MergeStrategy.last
        case s if s.endsWith("pom.properties") => MergeStrategy.last
        case s if s.endsWith("pom.xml") => MergeStrategy.last
        case s if s.endsWith(".jnilib") => MergeStrategy.rename
        case s if s.endsWith("jansi.dll") => MergeStrategy.rename
        case s if s.endsWith("libjansi.so") => MergeStrategy.rename
        case s if s.endsWith("properties") => MergeStrategy.filterDistinctLines
        case s if s.endsWith("xml") => MergeStrategy.last
        case x => (mergeStrategy in assembly).value(x)
    },
  )
