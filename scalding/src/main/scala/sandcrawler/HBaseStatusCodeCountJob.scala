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

class HBaseStatusCodeCountJob(args: Args) extends JobBase(args) with HBasePipeConversions {

  val source = HBaseCountJob.getHBaseSource(
    args("hbase-table"),
    args("zookeeper-hosts"),
    "grobid0:status_code")

  val statusPipe : TypedPipe[Long] = source
    .read
    .toTypedPipe[(ImmutableBytesWritable,ImmutableBytesWritable)]('key, 'status_code)
    .map { case (key, raw_code) => Bytes.toLong(raw_code.copyBytes()) }

  statusPipe.groupBy { identity }
    .size
    .debug
    .write(TypedTsv[(Long,Long)](args("output")))
}
