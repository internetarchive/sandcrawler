This directory contains Hadoop map/reduce jobs written in Scala (compiled to
the JVM) using the Scalding framework.

See the other markdown files in this directory for more background and tips.

## Building and Running

Locally, you need to have the JVM (eg, OpenJDK 1.8), `sbt` build tool, and
might need (exactly) Scala version 2.11.8.

See section below on building and installing custom SpyGlass jar.

Run tests:

    sbt test

Build a jar and upload to a cluster machine (from which to run in production):

    sbt assembly
    scp target/scala-2.11/sandcrawler-assembly-0.2.0-SNAPSHOT.jar devbox:

Run on cluster:

    devbox$ touch thing.conf
    devbox$ hadoop jar sandcrawler-assembly-0.2.0-SNAPSHOT.jar \
        com.twitter.scalding.Tool sandcrawler.HBaseRowCountJob --hdfs \
        --app.conf.path thing.conf \
        --output hdfs:///user/bnewbold/spyglass_out_test 
        
If your `sbt` task fails with this error:

     java.util.concurrent.ExecutionException: java.lang.OutOfMemoryError: Metaspace

try restarting `sbt` with more memory (e.g., `sbt -mem 2048`).

## SpyGlass Jar

SpyGlass is a "scalding-to-HBase" connector. It isn't maintained, so we needed
to rebuild to support our versions of HBase/scalding/etc. Our fork (including
build instructions) is at <https://github.com/bnewbold/SpyGlass>
(`bnewbold-scala2.11` branch); compiled .jar files are available from
<https://archive.org/download/ia_sandcrawler_maven2>.
