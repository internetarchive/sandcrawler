package sandcrawler

import cascading.property.AppProps
import cascading.tuple.Fields
import com.twitter.scalding._
import java.util.Properties
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.{HBaseSource, HBasePipeConversions}
import parallelai.spyglass.hbase.HBaseConstants.SourceMode

class HBaseCountJob(args: Args, colSpec: String) extends JobBase(args) with HBasePipeConversions {
  val output = args("output")
  HBaseBuilder.parseColSpec(colSpec)
  val Col: String = colSpec.split(":")(1)

  HBaseCountJob.getHBaseSource(args("hbase-table"),
                               args("zookeeper-hosts"),
                               colSpec)
    .read
    .fromBytesWritable(Symbol(Col))
    .debug
    .groupBy(Col){group => group.size('count)}
    .write(Tsv(output))
}

object HBaseCountJob {
  def getHBaseSource(hbase_table: String, zookeeper_hosts: String, colSpec: String) = HBaseBuilder.build(
    hbase_table,      // HBase Table Name
    zookeeper_hosts,  // HBase Zookeeper server (to get runtime config info; can be array?)
    List(colSpec),
    SourceMode.SCAN_ALL)
}
