
## Why Scalding

Scalding vs. Java (MapReduce) vs. Java (Cascading) vs. Scoobi vs. Scrunch:

- <https://speakerdeck.com/agemooij/why-hadoop-mapreduce-needs-scala?slide=34>
- <https://github.com/twitter/scalding/wiki/Comparison-to-Scrunch-and-Scoobi>

## Tips/Gotchas

`.scala` file names should match internal classes.

This project used to be called `scald-mvp`; now it's `sandcrawler`.

## Dev Environment

Versions running on Bryan's Debian/Linux laptop:

    openjdk version "1.8.0_171"
    OpenJDK Runtime Environment (build 1.8.0_171-8u171-b11-1~deb9u1-b11)
    OpenJDK 64-Bit Server VM (build 25.171-b11, mixed mode)

    Scala code runner version 2.11.8 -- Copyright 2002-2016, LAMP/EPFL

    sbt: 1.1.5

Scala was installed via regular debian (stretch) `apt` repository; `sbt` using
a bintray.com apt repo linked from the sbt website.

## Creating a new project

    sbt new scala/scala-seed.g8

    # inserted additional deps, tweaked versions
    # hadoop 2.5.0 seems to conflict with cascading; sticking with 2.6.0

    sbt assembly
    scp target/scala-2.11/scald-mvp-assembly-0.1.0-SNAPSHOT.jar devbox:

## Invoking on IA Cluster (old)

This seemed to work (from scalding repo):

    yarn jar tutorial/execution-tutorial/target/scala-2.11/execution-tutorial-assembly-0.18.0-SNAPSHOT.jar Tutorial1 --hdfs --input test_cdx --output test_scalding_out1

Or, with actual files on hadoop:

    yarn jar tutorial/execution-tutorial/target/scala-2.11/execution-tutorial-assembly-0.18.0-SNAPSHOT.jar Tutorial1 --hdfs --input hdfs:///user/bnewbold/dummy.txt --output hdfs:///user/bnewbold/test_scalding_out2

Horray! One issue with this was that building scalding took *forever* (meaning
30+ minutes).

potentially instead:

    hadoop jar scald-mvp-assembly-0.1.0-SNAPSHOT.jar com.twitter.scalding.Tool main.scala.example.WordCountJob --hdfs --input hdfs:///user/bnewbold/dummy.txt --output hdfs:///user/bnewbold/test_scalding_out2

Hypothesis: class name should be same as file name. Don't need `main` function
if using Scalding Tool wrapper jar. Don't need scald.rb.

    hadoop jar scald-mvp-assembly-0.1.0-SNAPSHOT.jar com.twitter.scalding.Tool example.WordCount --hdfs --input hdfs:///user/bnewbold/dummy.txt --output hdfs:///user/bnewbold/test_scalding_out2


## Scalding Repo

Got started by compiling and running examples (eg, Tutorial0) from the
`twitter/scalding` upstream repo. That repo has some special magic: a `./sbt`
wrapper script, and a `scripts/scald.rb` ruby script for invoking specific
jobs. Didn't end up being necessary.

Uncommenting this line in scalding:build.sbt sped things way up (don't need to
run *all* the tests):

       // Uncomment if you don't want to run all the tests before building assembly
       // test in assembly := {},

Also get the following error (in a different context):

    bnewbold@orithena$ sbt new typesafehub/scala-sbt
    [info] Loading project definition from /home/bnewbold/src/scala-sbt.g8/project/project
    [info] Compiling 1 Scala source to /home/bnewbold/src/scala-sbt.g8/project/project/target/scala-2.9.1/sbt-0.11.2/classes...
    [error] error while loading CharSequence, class file '/usr/lib/jvm/java-8-openjdk-amd64/jre/lib/rt.jar(java/lang/CharSequence.class)' is broken
    [error] (bad constant pool tag 18 at byte 10)
    [error] one error found
    [error] {file:/home/bnewbold/src/scala-sbt.g8/project/project/}default-46da7b/compile:compile: Compilation failed
    Project loading failed: (r)etry, (q)uit, (l)ast, or (i)gnore?  

## Resources

Whole bunch of example commands (sbt, maven, gradle) to build scalding:

    https://medium.com/@gayani.nan/how-to-run-a-scalding-job-567160fa193

Also looks good:

    https://blog.matthewrathbone.com/2015/10/20/scalding-tutorial.html

Possibly related:

    http://sujitpal.blogspot.com/2012/08/scalding-for-impatient.html
