
package sandcrawler

import cascading.flow.FlowDef
import cascading.pipe.Pipe
import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import org.apache.hadoop.hbase.io.ImmutableBytesWritable
import org.apache.hadoop.hbase.util.Bytes
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource

class GrobidScorableDumpJob(args: Args) extends JobBase(args) {

  val grobidHbaseRows = Stat("hbase-rows-scanned", "hbase-grobid-dump")
  val filteredGrobidRows = Stat("grobid-rows-filtered", "hbase-grobid-dump")
  val parsedGrobidRows = Stat("grobid-rows-parsed", "hbase-grobid-dump")
  val validGrobidRows = Stat("grobid-rows-valid-slug", "hbase-grobid-dump")

  val pipe = GrobidScorable.getHBaseSource(args("hbase-table"), args("zookeeper-hosts"))
    .read
    // Can't just "fromBytesWritable" because we have multiple types?
    .toTypedPipe[(ImmutableBytesWritable,ImmutableBytesWritable,ImmutableBytesWritable)](new Fields("key", "metadata", "status_code"))
    .filter { case (_, metadata, status_code) =>
      grobidHbaseRows.inc
      metadata != null && status_code != null
    }
    .map { case (key, metadata, status_code) =>
      (Bytes.toString(key.copyBytes()), Bytes.toString(metadata.copyBytes()), Bytes.toLong(status_code.copyBytes()))
    }
    // TODO: Should I combine next two stages for efficiency?
    .collect { case (key, json, 200) =>
      filteredGrobidRows.inc
      (key, json)
    }
    .map { entry : (String, String) =>
      parsedGrobidRows.inc
      GrobidScorable.jsonToMapFeatures(entry._1, entry._2)
    }
    .filter { entry => Scorable.isValidSlug(entry.slug) }
    .map { entry =>
      validGrobidRows.inc
      entry
    }
    // XXX: this groupBy after the map?
    .groupBy { case MapFeatures(slug, json) => slug }
    .map { tuple =>
      val (slug : String, features : MapFeatures) = tuple
      (slug, ReduceFeatures(features.json))
    }

  pipe
    .map { case (slug, features) =>
      (slug, features.json)
    }
    .write(TypedTsv[(String, String)](args("output")))
}
