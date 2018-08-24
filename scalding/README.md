This directory contains Hadoop map/reduce jobs written in Scala (compiled to
the JVM) using the Scalding framework. Scalding builds on the Java Cascading
library, which itself builds on the Java Hadoop libraries.

See the other markdown files in this directory for more background and tips.

## Dependencies

To develop locally, you need to have the JVM (eg, OpenJDK 1.8), `sbt` build
tool, and might need (exactly) Scala version 2.11.8.

On a debian/ubuntu machine:

    echo "deb https://dl.bintray.com/sbt/debian /" | sudo tee -a /etc/apt/sources.list.d/sbt.list
    sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 2EE0EA64E40A89B84B2DF73499E82A75642AC823
    sudo apt-get update
    sudo apt install scala sbt

It's also helpful to have a local copy of the `hadoop` binary for running
benchmarks. The `fetch_hadoop.sh` script in the top level directory will fetch
an appropriate version.

## Building and Running

You can run `sbt` commands individually:

    # run all test
    sbt test

    # build a jar (also runs tests)
    sbt assembly

Or you can start a session and run commands within that, which is *much*
faster:

    sbt -mem 2048

    sbt> test
    sbt> assembly
    sbt> testOnly sandcrawler.SomeTestClassName

On the cluster, you usually use the `please` script to kick off jobs. Be sure
to build the jars first, or pass `--rebuild` to do it automatically. You need
`hadoop` on your path for this.

## Troubleshooting

If your `sbt` task fails with this error:

     java.util.concurrent.ExecutionException: java.lang.OutOfMemoryError: Metaspace

try restarting `sbt` with more memory (e.g., `sbt -mem 2048`).

See `scalding-debugging.md` or maybe `../notes/` for more.
