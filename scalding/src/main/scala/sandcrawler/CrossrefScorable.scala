package sandcrawler

import cascading.flow.FlowDef
import cascading.pipe.Pipe
import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource
import TDsl._
import scala.util.parsing.json.JSONObject

import java.text.Normalizer
import java.util.Arrays
import java.util.Properties
import java.util.regex.Pattern

import scala.math
import scala.util.parsing.json.JSON
import scala.util.parsing.json.JSONObject

import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.CoGrouped
import com.twitter.scalding.typed.Grouped
import com.twitter.scalding.typed.TDsl._
import org.apache.hadoop.hbase.io.ImmutableBytesWritable
import org.apache.hadoop.hbase.util.Bytes
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource

class CrossrefScorable extends Scorable with HBasePipeConversions {
  // TODO: Generalize args so there can be multiple Crossref pipes in one job.
  def getSource(args : Args) : Source = {
    TextLine(args("crossref-input"))
  }

  def getFeaturesPipe(args : Args)(implicit mode : Mode, flowDef : FlowDef) : TypedPipe[MapFeatures] = {
    getSource(args).read
      .toTypedPipe[String](new Fields("line"))
      .map { CrossrefScorable.jsonToMapFeatures(_) }
  }
}

object CrossrefScorable {
  def jsonToMapFeatures(json : String) : MapFeatures = {
    Scorable.jsonToMap(json) match {
      case None => MapFeatures(Scorable.NoSlug, json)
      case Some(map) => {
        if ((map contains "titles") && (map contains "DOI")) {
          val titles = map("titles").asInstanceOf[List[String]]
          val doi = Scorable.getString(map, "DOI")
          if (titles.isEmpty || titles == null || doi.isEmpty || doi == null) {
            new MapFeatures(Scorable.NoSlug, json)
          } else {
            val title = titles(0)
            val map2 = Scorable.toScorableMap(title=title, doi=doi)
            new MapFeatures(
              Scorable.mapToSlug(map2),
              JSONObject(map2).toString)
          }
        } else {
          new MapFeatures(Scorable.NoSlug, json)
        }
      }
    }
  }
}
