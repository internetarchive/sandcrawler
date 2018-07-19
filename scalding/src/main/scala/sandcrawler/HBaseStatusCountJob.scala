package sandcrawler

import java.util.Properties

import cascading.property.AppProps
import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import org.apache.hadoop.hbase.io.ImmutableBytesWritable
import org.apache.hadoop.hbase.util.Bytes
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.BasePipeConversions
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBaseSource

class HBaseStatusCountJob(args: Args) extends JobBase(args) with HBasePipeConversions {

  val colSpec = "grobid0:status_code"
  val output = args("output")
  HBaseBuilder.parseColSpec(colSpec)
  val Col: String = colSpec.split(":")(1)

  val source : TypedPipe[Long] = HBaseCountJob.getHBaseSource(
    args("hbase-table"),
    args("zookeeper-hosts"),
    colSpec)
    .read
    .toTypedPipe[(ImmutableBytesWritable,ImmutableBytesWritable)]('key, 'status_code)
    .map { case (key, raw_code) => Bytes.toLong(raw_code.copyBytes()) }

  source.groupBy { identity }
    .size
    .debug
    .write(TypedTsv[(Long,Long)](output))
}
