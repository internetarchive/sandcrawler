package sandcrawler

import cascading.property.AppProps
import cascading.tuple.Fields
import com.twitter.scalding._
import java.util.Properties
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.{HBaseSource, HBasePipeConversions}
import parallelai.spyglass.hbase.HBaseConstants.SourceMode

class HBaseStatusCountJob(args: Args) extends JobBase(args) with HBasePipeConversions {
  val output = args("output")

  HBaseStatusCountJob.getHBaseSource
    .read
    .fromBytesWritable(List('status))
//    .debug
    .groupBy('status){group => group.size('count)}
    .write(Tsv(output))
}

object HBaseStatusCountJob {
  def getHBaseSource = HBaseBuilder.build(
    "wbgrp-journal-extract-0-qa",     // HBase Table Name
    "mtrcs-zk1.us.archive.org:2181",  // HBase Zookeeper server (to get runtime config info; can be array?)
    List("grobid0:status"),
    SourceMode.SCAN_ALL)
}
