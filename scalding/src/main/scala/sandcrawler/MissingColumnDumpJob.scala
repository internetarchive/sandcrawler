package sandcrawler

import java.util.Properties

import cascading.property.AppProps
import cascading.tuple.Fields
import com.twitter.scalding._
import org.apache.hadoop.hbase.util.Bytes
import org.apache.hadoop.hbase.client.Scan
import org.apache.hadoop.hbase.filter.SingleColumnValueFilter
import org.apache.hadoop.hbase.filter.CompareFilter
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseRawSource
import parallelai.spyglass.hbase.HBaseSource

class MissingColumnDumpJob(args: Args) extends JobBase(args) with HBasePipeConversions {

  val output = args("output")

  MissingColumnDumpJob.getHBaseSource(
    args("hbase-table"),
    args("zookeeper-hosts"),
    args("column"))
    .read
    .fromBytesWritable('key)
    .write(Tsv(output))
}

object MissingColumnDumpJob {

  // eg, "wbgrp-journal-extract-0-qa",7 "mtrcs-zk1.us.archive.org:2181"
  def getHBaseSource(hbaseTable: String, zookeeperHosts: String, col: String) : HBaseSource = {

    val colFamily = col.split(":")(0)
    val colColumn = col.split(":")(1)
    val scan = new Scan
    val filter = new SingleColumnValueFilter(
      Bytes.toBytes(colFamily),
      Bytes.toBytes(colColumn),
      CompareFilter.CompareOp.EQUAL,
      Bytes.toBytes("")
    )
    filter.setFilterIfMissing(false)
    scan.setFilter(filter)
    val scanner = HBaseRawSource.convertScanToString(scan)
    val (families, fields) = HBaseBuilder.parseColSpecs(List("f:c", col))

    new HBaseRawSource(
      hbaseTable,
      zookeeperHosts,
      new Fields("key"),
      families,
      fields,
      SourceMode.SCAN_ALL,
      base64Scan = scanner)
  }
}
