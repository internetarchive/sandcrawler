package sandcrawler

import com.twitter.scalding._
import parallelai.spyglass.hbase.{HBaseSource, HBasePipeConversions, HBaseConstants}

class HBaseRowCountJob(args: Args) extends Job(args) {

  // For now doesn't actually count, just dumps a "word count"

  val hbs = new HBaseSource(
    "wbgrp-journal-extract-0-qa",     // HBase Table Name
    "mtrcs-zk1.us.archive.org:2181",  // HBase Zookeeper server (to get runtime config info; can be array?)
    'key,                             // ... then a list of column names
    sourceMode = HBaseConstants.SourceMode.SCAN_ALL)
/*
    .read
    .map { word => (word, 1L) }
    .sumByKey
    .write(TypedTsv[(String, Long)](args("output")))
    // The compiler will enforce the type coming out of the sumByKey is the same as the type we have for our sink
    .flatMap { line => line.split("\\s+") }
*/
}
