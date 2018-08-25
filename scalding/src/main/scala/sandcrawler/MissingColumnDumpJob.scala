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

// This nasty, no-good, horrible Job outputs a list of keys ("sha1:A234...")
// for which the given "column" does not have a value set.
// It does this using a self-join because SpyGlass's HBase SCAN support seems
// to be extremely limited.
class MissingColumnDumpJob(args: Args) extends JobBase(args) with HBasePipeConversions {

  val output = args("output")

  val allKeys : TypedPipe[String] = MissingColumnDumpJob.getHBaseKeySource(
    args("hbase-table"),
    args("zookeeper-hosts"))
    .read
    .fromBytesWritable('key)
    .toTypedPipe[String]('key)

  val existingKeys : TypedPipe[(String,Boolean)] = MissingColumnDumpJob.getHBaseColSource(
    args("hbase-table"),
    args("zookeeper-hosts"),
    args("column"))
    .read
    .fromBytesWritable('key)
    .toTypedPipe[String]('key)
    .map{ key => (key, true) }

  val missingKeys : TypedPipe[String] = allKeys
    .groupBy( identity )
    .leftJoin(existingKeys.groupBy(_._1))
    .toTypedPipe
    .collect { case (key, (_, None)) => key }

  missingKeys
    .write(TypedTsv[String](output))

}

object MissingColumnDumpJob {

  // eg, "wbgrp-journal-extract-0-qa",7 "mtrcs-zk1.us.archive.org:2181"
  def getHBaseColSource(hbaseTable: String, zookeeperHosts: String, col: String) : HBaseSource = {
    HBaseBuilder.build(
      hbaseTable,
      zookeeperHosts,
      List(col),
      SourceMode.SCAN_ALL)
  }

  def getHBaseKeySource(hbaseTable: String, zookeeperHosts: String) : HBaseSource = {
    HBaseBuilder.build(
      hbaseTable,
      zookeeperHosts,
      List("f:c"),
      SourceMode.SCAN_ALL)
  }
}
