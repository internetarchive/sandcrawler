package sandcrawler

import java.util.Properties

import cascading.property.AppProps
import cascading.tuple.Fields
import com.twitter.scalding._
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource

class HBaseCountJob(args: Args, colSpec: String) extends JobBase(args) with HBasePipeConversions {
  val output = args("output")
  HBaseBuilder.parseColSpec(colSpec)
  val Col: String = colSpec.split(":")(1)

  HBaseCountJob.getHBaseSource(
    args("hbase-table"),
    args("zookeeper-hosts"),
    colSpec)
    .read
    .fromBytesWritable(Symbol(Col))
    .debug
    .groupBy(Col){group => group.size('count)}
    .write(Tsv(output))
}

object HBaseCountJob {
  def getHBaseSource(hbaseTable: String, zookeeperHosts: String, colSpec: String) : HBaseSource = HBaseBuilder.build(
    hbaseTable,      // HBase Table Name
    zookeeperHosts,  // HBase Zookeeper server (to get runtime config info; can be array?)
    List(colSpec),
    SourceMode.SCAN_ALL)
}
