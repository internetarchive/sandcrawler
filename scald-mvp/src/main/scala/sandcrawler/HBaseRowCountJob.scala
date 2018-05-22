package sandcrawler

import com.twitter.scalding._
import parallelai.spyglass.hbase.{HBaseSource, HBasePipeConversions, HBaseConstants}
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import cascading.tuple.Fields

class HBaseRowCountJob(args: Args) extends Job(args) with HBasePipeConversions {

  // For now doesn't actually count, just dumps a "word count"

  val output = args("output")

  val hbs = new HBaseSource(
    "wbgrp-journal-extract-0-qa",     // HBase Table Name
    "mtrcs-zk1.us.archive.org:2181",  // HBase Zookeeper server (to get runtime config info; can be array?)
     new Fields("key"),
     List("column_family"),
    sourceMode = SourceMode.SCAN_ALL)
    .read
    .debug
    .fromBytesWritable(new Fields("key"))
    .write(Tsv(output format "get_list"))
}
