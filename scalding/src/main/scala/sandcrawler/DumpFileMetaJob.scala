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

// Dumps all the info needed to insert a file entity in Fatcat. Useful for
// joining.
class DumpFileMetaJob(args: Args) extends JobBase(args) with HBasePipeConversions {

  val metaPipe : TypedPipe[(String, String, String, Long)] = HBaseBuilder.build(args("hbase-table"),
                     args("zookeeper-hosts"),
                     List("file:cdx", "file:mime", "file:size"),
                     SourceMode.SCAN_ALL)
    .read
    .toTypedPipe[(ImmutableBytesWritable,ImmutableBytesWritable,ImmutableBytesWritable,ImmutableBytesWritable)](new Fields("key", "cdx", "mime", "size"))
    .filter { case (_, cdx, mime, size) => cdx != null && mime != null && size != null }
    .map { case (key, cdx, mime, size) =>
      (Bytes.toString(key.copyBytes()),
       Bytes.toString(cdx.copyBytes()),
       Bytes.toString(mime.copyBytes()),
       Bytes.toLong(size.copyBytes()))
    };

  metaPipe.write(TypedTsv[(String,String,String,Long)](args("output")))

}
