package sandcrawler

import cascading.flow.FlowDef
import cascading.pipe.Pipe
import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource

class GrobidScorable extends Scorable with HBasePipeConversions {
  def getFeaturesPipe(args : Args)(implicit flowDef : FlowDef, mode : Mode) : TypedPipe[MapFeatures] = {
    // TODO: Clean up code after debugging.
    val grobidSource = HBaseBuilder.build(
      args("hbase-table"),
      args("zookeeper-hosts"),
      List("grobid0:tei_json"),
      SourceMode.SCAN_ALL)

    grobidSource.read
      .fromBytesWritable(new Fields("key", "tei_json"))
    // TODO: Figure out why this line (used in HBaseCrossrefScoreJob.scala)
    // didn't work here: .toTypedPipe[(String, String)]('key, 'tei_json)
      .toTypedPipe[(String, String)](new Fields("key", "tei_json"))
      .map { entry =>
        val (key : String, json : String) = (entry._1, entry._2)
        GrobidScorable.grobidToSlug(json) match {
          case Some(slug) => new MapFeatures(slug, json)
          case None => new MapFeatures(Scorable.NoSlug, json)
        }
      }
  }
}

object GrobidScorable {
  def grobidToSlug(json : String) : Option[String] = {
    Scorable.jsonToMap(json) match {
      case None => None
      case Some(map) => {
        if (map contains "title") {
          Some(Scorable.titleToSlug(map("title").asInstanceOf[String]))
        } else {
          None
        }
      }
    }
  }
}

