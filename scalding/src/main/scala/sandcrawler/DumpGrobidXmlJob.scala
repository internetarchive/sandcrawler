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
import scala.util.parsing.json.JSONObject

// Dumps the SHA1 key and grobid0:tei_xml columns, as TSV/JSON (two TSV
// columns: one is key, second is JSON). Used for partner delivery/sharing
class DumpGrobidXmlJob(args: Args) extends JobBase(args) with HBasePipeConversions {

  val metaPipe : TypedPipe[(String, String)] = HBaseBuilder.build(args("hbase-table"),
                     args("zookeeper-hosts"),
                     List("file:cdx", "grobid0:tei_xml"),
                     SourceMode.SCAN_ALL)
    .read
    .toTypedPipe[(ImmutableBytesWritable,ImmutableBytesWritable,ImmutableBytesWritable)](new Fields("key", "cdx", "tei_xml"))
    .filter { case (_, cdx, tei_xml) => cdx != null && tei_xml != null }
    .map { case (key, cdx, tei_xml) =>
      (Bytes.toString(key.copyBytes()),
       JSONObject(
        Map(
          "pdf_hash" -> Bytes.toString(key.copyBytes()),
          "cdx_metadata" -> Bytes.toString(key.copyBytes()),
          "tei_xml" -> Bytes.toString(key.copyBytes())
        )).toString
      )
    };

  metaPipe.write(TypedTsv[(String,String)](args("output")))

}
