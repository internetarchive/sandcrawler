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
  def getFeaturesPipe(args : Args)(implicit flowDef : FlowDef, mode : Mode) = {
//    val crossrefSource = TextLine(args("crossref-input"))
//    val crossrefPipe : TypedPipe[MapFeatures] = crossrefSource
    TextLine(args("crossref-input"))
      .read
      .toTypedPipe[String](new Fields("line"))
      .map{ json : String =>
        HBaseCrossrefScore.crossrefToSlug(json) match {
          case Some(slug) => new MapFeatures(slug, json)
          case None => new MapFeatures(Scorable.NoSlug, json)
        }
      }
//    crossrefPipe
  }
}
