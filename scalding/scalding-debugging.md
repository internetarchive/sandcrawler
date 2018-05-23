
Quick tips for debugging scalding issues...

## Dependencies

Print the dependency graph (using the `sbt-dependency-graph` plugin):

    sbt dependencyTree

## Old Errors

At one phase, was getting `NullPointerException` errors when running tests or
in production, like:

    bnewbold@bnewbold-dev$ hadoop jar scald-mvp-assembly-0.1.0-SNAPSHOT.jar com.twitter.scalding.Tool sandcrawler.HBaseRowCountJob --hdfs --output hdfs:///user/bnewbold/spyglass_out_test
    Exception in thread "main" java.lang.Throwable: If you know what exactly caused this error, please consider contributing to GitHub via following link.
    https://github.com/twitter/scalding/wiki/Common-Exceptions-and-possible-reasons#javalangnullpointerexception
            at com.twitter.scalding.Tool$.main(Tool.scala:152)
            at com.twitter.scalding.Tool.main(Tool.scala)
            at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)
            at sun.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:62)
            at sun.reflect.DelegatingMethodAccessorImpl.invoke(DelegatingMethodAccessorImpl.java:43)
            at java.lang.reflect.Method.invoke(Method.java:498)
            at org.apache.hadoop.util.RunJar.main(RunJar.java:212)
    Caused by: java.lang.reflect.InvocationTargetException
            at sun.reflect.NativeConstructorAccessorImpl.newInstance0(Native Method)
            at sun.reflect.NativeConstructorAccessorImpl.newInstance(NativeConstructorAccessorImpl.java:62)
            at sun.reflect.DelegatingConstructorAccessorImpl.newInstance(DelegatingConstructorAccessorImpl.java:45)
            at java.lang.reflect.Constructor.newInstance(Constructor.java:423)
            at com.twitter.scalding.Job$.apply(Job.scala:44)
            at com.twitter.scalding.Tool.getJob(Tool.scala:49)
            at com.twitter.scalding.Tool.run(Tool.scala:68)
            at org.apache.hadoop.util.ToolRunner.run(ToolRunner.java:70)
            at com.twitter.scalding.Tool$.main(Tool.scala:148)
            ... 6 more
    Caused by: java.lang.NullPointerException
            at parallelai.spyglass.hbase.HBaseSource.<init>(HBaseSource.scala:48)
            at sandcrawler.HBaseRowCountJob.<init>(HBaseRowCountJob.scala:14)
            ... 15 more

This was resolved by ensuring that all required parameters were being passed to
the `HBaseSource` constructor.

Another time, saw a bunch of `None.get` errors when running tests. These were
resolved by ensuring that the `HBaseSource` constructors had exactly identical
names and arguments (eg, table names and zookeeper quorums have to be exact
matches).
