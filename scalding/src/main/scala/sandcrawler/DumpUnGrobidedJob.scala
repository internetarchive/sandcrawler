package sandcrawler

import java.util.Properties

import cascading.property.AppProps
import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource

// Filters for HBase rows which have not had GROBID run on them, but do have
// full CDX metadata, and dumps to a TSV for later extraction by the
// "extraction-ungrobided" job.
//
// Does the same horrible join thing that DumpUnGrobidedJob does.
class DumpUnGrobidedJob(args: Args) extends JobBase(args) with HBasePipeConversions {

  val output = args("output")

  val allKeys : TypedPipe[(String,String,String,String)] = DumpUnGrobidedJob.getHBaseKeySource(
    args("hbase-table"),
    args("zookeeper-hosts"))
    .read
    .fromBytesWritable('key, 'c, 'mime, 'cdx)
    .toTypedPipe[(String,String,String,String)]('key, 'c, 'mime, 'cdx)

  val existingKeys : TypedPipe[(String,Boolean)] = DumpUnGrobidedJob.getHBaseColSource(
    args("hbase-table"),
    args("zookeeper-hosts"))
    .read
    .fromBytesWritable('key)
    .toTypedPipe[String]('key)
    .map{ key => (key, true) }

  val missingKeys : TypedPipe[(String,String,String,String)] = allKeys
    .groupBy(_._1)
    .leftJoin(existingKeys.groupBy(_._1))
    .toTypedPipe
    .collect { case (key, ((_, c, mime, cdx), None)) => (key, c, mime, cdx) }

  missingKeys
    .write(TypedTsv[(String,String,String,String)](output))

}

object DumpUnGrobidedJob {

  // eg, "wbgrp-journal-extract-0-qa",7 "mtrcs-zk1.us.archive.org:2181"
  def getHBaseColSource(hbaseTable: String, zookeeperHosts: String) : HBaseSource = {
    HBaseBuilder.build(
      hbaseTable,
      zookeeperHosts,
      List("grobid0:status_code"),
      SourceMode.SCAN_ALL)
  }

  def getHBaseKeySource(hbaseTable: String, zookeeperHosts: String) : HBaseSource = {
    HBaseBuilder.build(
      hbaseTable,
      zookeeperHosts,
      List("f:c", "file:mime", "file:cdx"),
      SourceMode.SCAN_ALL)
  }
}
