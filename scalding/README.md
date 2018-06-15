This directory contains Hadoop map/reduce jobs written in Scala (compiled to
the JVM) using the Scalding framework.

See the other markdown files in this directory for more background and tips.

## Dependencies

Locally, you need to have the JVM (eg, OpenJDK 1.8), `sbt` build tool, and
might need (exactly) Scala version 2.11.8.

On a debian/ubuntu machine:

    echo "deb https://dl.bintray.com/sbt/debian /" | sudo tee -a /etc/apt/sources.list.d/sbt.list
    sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 2EE0EA64E40A89B84B2DF73499E82A75642AC823
    sudo apt-get update
    sudo apt install scala sbt

## Building and Running

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

## Troubleshooting

If your `sbt` task fails with this error:

     java.util.concurrent.ExecutionException: java.lang.OutOfMemoryError: Metaspace

try restarting `sbt` with more memory (e.g., `sbt -mem 2048`).

