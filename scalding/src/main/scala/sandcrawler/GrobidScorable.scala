package sandcrawler

import scala.util.parsing.json.JSONObject

import cascading.flow.FlowDef
import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import org.apache.hadoop.hbase.io.ImmutableBytesWritable
import org.apache.hadoop.hbase.util.Bytes
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource

class GrobidScorable extends Scorable with HBasePipeConversions {
  val StatusOK = 200

  def getSource(args : Args) : Source = {
    // TODO: Generalize args so there can be multiple grobid pipes in one job.
    GrobidScorable.getHBaseSource(args("hbase-table"), args("zookeeper-hosts"))
  }

  def getFeaturesPipe(args : Args)(implicit mode : Mode, flowDef : FlowDef) : TypedPipe[MapFeatures] = {
    getSource(args)
      .read
      // Can't just "fromBytesWritable" because we have multiple types?
      .toTypedPipe[(ImmutableBytesWritable,ImmutableBytesWritable,ImmutableBytesWritable)](new Fields("key", "metadata", "status_code"))
      .filter { case (_, metadata, status_code) => metadata != null && status_code != null }
      .map { case (key, metadata, status_code) =>
        (Bytes.toString(key.copyBytes()), Bytes.toString(metadata.copyBytes()), Bytes.toLong(status_code.copyBytes()))
      }
      // TODO: Should I combine next two stages for efficiency?
      .collect { case (key, json, StatusOK) => (key, json) }
      .map { entry : (String, String) => GrobidScorable.jsonToMapFeatures(entry._1, entry._2) }
  }
}

object GrobidScorable {
  def getHBaseSource(table : String, host : String) : HBaseSource = {
    HBaseBuilder.build(table, host, List("grobid0:metadata", "grobid0:status_code"), SourceMode.SCAN_ALL)
  }

  def jsonToMapFeatures(key : String, json : String) : MapFeatures = {
    Scorable.jsonToMap(json) match {
      case None => MapFeatures(Scorable.NoSlug, json)
      case Some(map) => {
        if (map contains "title") {
          ScorableFeatures.create(title=Scorable.getString(map, "title"), sha1=key).toMapFeatures
        } else {
          MapFeatures(Scorable.NoSlug, json)
        }
      }
    }
  }
}

