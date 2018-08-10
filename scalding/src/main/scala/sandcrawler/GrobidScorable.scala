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
  def getSource(args : Args) : Source = {
    // TODO: Generalize args so there can be multiple grobid pipes in one job.
    GrobidScorable.getHBaseSource(args("hbase-table"), args("zookeeper-hosts"))
  }

  def getFeaturesPipe(pipe : Pipe) : TypedPipe[MapFeatures] = {
    pipe
      .fromBytesWritable(new Fields("key", "tei_json"))
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
  def getHBaseSource(table : String, host : String) : HBaseSource = {
    HBaseBuilder.build(table, host, List("grobid0:tei_json"), SourceMode.SCAN_ALL)
  }

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

