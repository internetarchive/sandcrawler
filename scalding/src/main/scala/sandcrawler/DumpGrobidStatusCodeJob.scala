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

// Dumps status code for each GROBID-processed file. Good for crawl/corpus
// analytics, if we consider GROBID status a rough "is this a paper" metric.
class DumpGrobidStatusCodeJob(args: Args) extends JobBase(args) with HBasePipeConversions {

  val metaPipe : TypedPipe[(String, Long)] = HBaseBuilder.build(args("hbase-table"),
                     args("zookeeper-hosts"),
                     List("grobid0:status_code"),
                     SourceMode.SCAN_ALL)
    .read
    .toTypedPipe[(ImmutableBytesWritable,ImmutableBytesWritable)](new Fields("key", "status_code"))
    .filter { case (_, status_code) => status_code != null }
    .map { case (key, status_code) =>
      (Bytes.toString(key.copyBytes()),
       Bytes.toLong(status_code.copyBytes()))
    };

  metaPipe.write(TypedTsv[(String,Long)](args("output")))

}
