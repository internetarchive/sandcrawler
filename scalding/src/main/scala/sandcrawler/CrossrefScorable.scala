package sandcrawler

import scala.math
import scala.util.parsing.json.JSON
import scala.util.parsing.json.JSONObject

import cascading.flow.FlowDef
import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import parallelai.spyglass.hbase.HBasePipeConversions

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
        if ((map contains "title") && (map contains "DOI")) {
          val titles = map("title").asInstanceOf[List[String]]
          val doi = Scorable.getString(map, "DOI")
          if (titles.isEmpty || titles == null || doi.isEmpty || doi == null) {
            new MapFeatures(Scorable.NoSlug, json)
          } else {
            // bnewbold: not checking that titles(0) is non-null/non-empty; case would be, in JSON, "title": [ null ]
            val sf : ScorableFeatures = ScorableFeatures.create(title=titles(0), doi=doi)
            new MapFeatures(sf.toSlug, sf.toString)
          }
        } else {
          new MapFeatures(Scorable.NoSlug, json)
        }
      }
    }
  }
}
