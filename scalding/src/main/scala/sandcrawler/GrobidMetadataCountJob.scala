package sandcrawler

import java.util.Properties

import cascading.property.AppProps
import cascading.tuple.Fields
import com.twitter.scalding._
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource

class GrobidMetadataCountJob(args: Args) extends JobBase(args) with HBasePipeConversions {

  val output = args("output")

  GrobidMetadataCountJob.getHBaseSource(
    args("hbase-table"),
    args("zookeeper-hosts"))
    .read
    .debug
    .groupAll { _.size('count) }
    .write(Tsv(output))
}

object GrobidMetadataCountJob {

  // eg, "wbgrp-journal-extract-0-qa",7 "mtrcs-zk1.us.archive.org:2181"
  def getHBaseSource(hbaseTable: String, zookeeperHosts: String) : HBaseSource = {
    HBaseBuilder.build(
      hbaseTable,
      zookeeperHosts,
      List("grobid0:metadata"),
      SourceMode.SCAN_ALL)
  }
}
