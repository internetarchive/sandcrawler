
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
    scp scp target/scala-2.11/scald-mvp-assembly-0.1.0-SNAPSHOT.jar devbox:

Run on cluster:

    devbox$ touch thing.conf
    devbox$ hadoop jar scald-mvp-assembly-0.1.0-SNAPSHOT.jar \
        com.twitter.scalding.Tool sandcrawler.HBaseRowCountJob --hdfs \
        --app.conf.path thing.conf \
        --output hdfs:///user/bnewbold/spyglass_out_test 

## Building SpyGlass Jar

SpyGlass is a "scalding-to-HBase" connector. It isn't maintained, so we needed
to rebuild to support our versions of HBase/scalding/etc. From SpyGlass fork
(<https://github.com/bnewbold/SpyGlass>,
`bnewbold-scala2.11` branch):

    cd ~/src/SpyGlass
    git checkout bnewbold-scala2.11

    # This builds the new .jar and installs it in the (laptop local) ~/.m2
    # repository
    mvn clean install -U

    # Copy that .jar (and associated pom.xml) over to where sbt can find it
    mkdir -p ~/.sbt/preloaded/parallelai/
    cp -r ~/.m2/repository/parallelai/parallelai.spyglass ~/.sbt/preloaded/parallelai/

The medium-term plan here is to push the custom SpyGlass jar as a static maven
repo to an archive.org item, and point build.sbt to that folder.

