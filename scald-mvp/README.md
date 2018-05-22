
following https://medium.com/@gayani.nan/how-to-run-a-scalding-job-567160fa193


running on my laptop:

    openjdk version "1.8.0_171"
    OpenJDK Runtime Environment (build 1.8.0_171-8u171-b11-1~deb9u1-b11)
    OpenJDK 64-Bit Server VM (build 25.171-b11, mixed mode)

    Scala code runner version 2.11.8 -- Copyright 2002-2016, LAMP/EPFL

    sbt: 1.1.5

    sbt new scala/scala-seed.g8

    # inserted additional deps, tweaked versions
    # hadoop 2.5.0 seems to conflict with cascading; sticking with 2.6.0

    sbt assembly
    scp target/scala-2.11/scald-mvp-assembly-0.1.0-SNAPSHOT.jar devbox:

    # on cluster:
    yarn jar scald-mvp-assembly-0.1.0-SNAPSHOT.jar WordCount --hdfs --input hdfs:///user/bnewbold/dummy.txt

later, using hadop command instead:

    hadoop jar scald-mvp-assembly-0.1.0-SNAPSHOT.jar com.twitter.scalding.Tool example.WordCountJob --hdfs --input hdfs:///user/bnewbold/dummy.txt --output hdfs:///user/bnewbold/test_scalding_out3

helpful for debugging dependency woes:

    sbt dependencyTree

## Custom build

in SpyGlass repo:

    # This builds the new .jar and installs it in the (laptop local) ~/.m2
    # repository
    mvn clean install -U

    # Copy that .jar (and associated pom.xml) over to where sbt can find it
    mkdir -p ~/.sbt/preloaded/parallelai/
    cp -r ~/.m2/repository/parallelai/parallelai.spyglass ~/.sbt/preloaded/parallelai/

    # then build here
    sbt assembly
