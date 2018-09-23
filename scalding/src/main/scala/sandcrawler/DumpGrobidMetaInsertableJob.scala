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

// Dumps the SHA1 key and grobid0:metadata columns, plus file metadata needed
// to insert into fatcat. Used, eg, as part of long-tail mellon pipeline.
class DumpGrobidMetaInsertableJob(args: Args) extends JobBase(args) with HBasePipeConversions {

  val metaPipe : TypedPipe[(String, String, String, Long, String)] = HBaseBuilder.build(args("hbase-table"),
                     args("zookeeper-hosts"),
                     List("file:cdx", "file:mime", "file:size", "grobid0:metadata"),
                     SourceMode.SCAN_ALL)
    .read
    .toTypedPipe[(ImmutableBytesWritable,ImmutableBytesWritable,ImmutableBytesWritable,ImmutableBytesWritable,ImmutableBytesWritable)](new Fields("key", "cdx", "mime", "size", "metadata"))
    .filter { case (_, cdx, mime, size, metadata) => cdx != null && mime != null && size != null && metadata != null }
    .map { case (key, cdx, mime, size, metadata) =>
      (Bytes.toString(key.copyBytes()),
       Bytes.toString(cdx.copyBytes()),
       Bytes.toString(mime.copyBytes()),
       Bytes.toLong(size.copyBytes()),
       Bytes.toString(metadata.copyBytes())
      )
    };

  metaPipe.write(TypedTsv[(String,String,String,Long,String)](args("output")))

}
