package sandcrawler

import java.util.Properties

import cascading.property.AppProps
import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import org.apache.hadoop.hbase.io.ImmutableBytesWritable
import org.apache.hadoop.hbase.util.Bytes
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource

class HBaseStatusCountJob(args: Args) extends JobBase(args) with HBasePipeConversions {

  val source = HBaseCountJob.getHBaseSource(
    args("hbase-table"),
    args("zookeeper-hosts"),
    "grobid0:status")

  val statusPipe : TypedPipe[String] = source
    .read
    .toTypedPipe[(ImmutableBytesWritable,ImmutableBytesWritable)]('key, 'status)
    .map { case (key, raw_status) => Bytes.toString(raw_status.copyBytes()) }

  statusPipe.groupBy { identity }
    .size
    .debug
    .write(TypedTsv[(String,Long)](args("output")))
}
