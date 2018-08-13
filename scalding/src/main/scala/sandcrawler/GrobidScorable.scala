package sandcrawler

import scala.util.parsing.json.JSONObject

import cascading.flow.FlowDef
import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource

class GrobidScorable extends Scorable with HBasePipeConversions {
  def getSource(args : Args) : Source = {
    // TODO: Generalize args so there can be multiple grobid pipes in one job.
    GrobidScorable.getHBaseSource(args("hbase-table"), args("zookeeper-hosts"))
  }

  def getFeaturesPipe(args : Args)(implicit mode : Mode, flowDef : FlowDef) : TypedPipe[MapFeatures] = {
    getSource(args)
      .read
      .fromBytesWritable(new Fields("key", "tei_json"))
      .toTypedPipe[(String, String)](new Fields("key", "tei_json"))
      .map { entry : (String, String) => GrobidScorable.jsonToMapFeatures(entry._1, entry._2) }
  }
}

object GrobidScorable {
  def getHBaseSource(table : String, host : String) : HBaseSource = {
    HBaseBuilder.build(table, host, List("grobid0:tei_json"), SourceMode.SCAN_ALL)
  }

  def jsonToMapFeatures(key : String, json : String) : MapFeatures = {
    Scorable.jsonToMap(json) match {
      case None => MapFeatures(Scorable.NoSlug, json)
      case Some(map) => {
        if (map contains "title") {
          val map2 = Scorable.toScorableMap(Scorable.getString(map, "title"),
            sha1=key)
          new MapFeatures(
            Scorable.mapToSlug(map2),
            JSONObject(map2).toString)
        } else {
          MapFeatures(Scorable.NoSlug, json)
        }
      }
    }
  }
}

