package sandcrawler

import java.util.Properties

import cascading.property.AppProps
import cascading.tuple.Fields
import com.twitter.scalding._
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource

class HBaseRowCountJob(args: Args) extends JobBase(args) with HBasePipeConversions {

  val output = args("output")

  HBaseRowCountJob.getHBaseSource(
    args("hbase-table"),
    args("zookeeper-hosts"))
    .read
    .debug
    .groupAll { _.size('count) }
    .write(Tsv(output))
}

object HBaseRowCountJob {

  // eg, "wbgrp-journal-extract-0-qa",7 "mtrcs-zk1.us.archive.org:2181"
  def getHBaseSource(hbaseTable: String, zookeeperHosts: String) : HBaseSource = {
    HBaseBuilder.build(
      hbaseTable,
      zookeeperHosts,
      List("f:c"),
      SourceMode.SCAN_ALL)
  }
}
