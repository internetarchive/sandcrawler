package sandcrawler

import com.twitter.scalding._
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.{HBaseSource, HBasePipeConversions, HBaseConstants}
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import cascading.tuple.Fields
import cascading.property.AppProps
import java.util.Properties


class HBaseRowCountJob(args: Args) extends JobBase(args) with HBasePipeConversions {


  // For now doesn't actually count, just dumps a "word count"

  val output = args("output")

  HBaseRowCountJob.getHBaseSource
    .read
    .debug
    .groupAll { _.size('count) }
    .write(Tsv(output))
}

object HBaseRowCountJob {
  def getHBaseSource = HBaseBuilder.build(
    "wbgrp-journal-extract-0-qa",     // HBase Table Name
    "mtrcs-zk1.us.archive.org:2181",  // HBase Zookeeper server (to get runtime config info; can be array?)
    List("file:size", "file:mime"),
    SourceMode.SCAN_ALL)
}
