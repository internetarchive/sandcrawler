package sandcrawler

import cascading.flow.FlowDef
import cascading.pipe.Pipe
import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource

class CrossrefScorable extends Scorable {
  def getFeaturesPipe(args : Args) : TypedPipe[MapFeatures] = {
    // TODO: Generalize args so there can be multiple Grobid pipes in one job.
    TextLine(args("crossref-input"))
      .read
      .toTypedPipe[String](new Fields("line"))
      .map{ json : String =>
        CrossrefScorable.crossrefToSlug(json) match {
          case Some(slug) => new MapFeatures(slug, json)
          case None => new MapFeatures(Scorable.NoSlug, json)
        }
      }
  }
}

object CrossrefScorable {
  def crossrefToSlug(json : String) : Option[String] = {
    Scorable.jsonToMap(json) match {
      case None => None
      case Some(map) => {
        if (map contains "title") {
          // TODO: Don't ignore titles after the first.
          val title = map("title").asInstanceOf[List[String]](0)
          Some(Scorable.titleToSlug(title))
        } else {
          None
        }
      }
    }
  }
}
