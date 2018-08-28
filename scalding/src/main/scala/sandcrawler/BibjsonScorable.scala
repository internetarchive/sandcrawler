package sandcrawler

import scala.math
import scala.util.parsing.json.JSON
import scala.util.parsing.json.JSONObject

import cascading.flow.FlowDef
import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._

class BibjsonScorable extends Scorable {

  def getSource(args : Args) : Source = {
    TextLine(args("bibjson-input"))
  }

  def getFeaturesPipe(args : Args)(implicit mode : Mode, flowDef : FlowDef) : TypedPipe[Option[MapFeatures]] = {
    getSource(args).read
      .toTypedPipe[String](new Fields("line"))
      .map { BibjsonScorable.bibjsonToMapFeatures(_) }
  }
}

object BibjsonScorable {
  def bibjsonToMapFeatures(json : String) : Option[MapFeatures] = {
    Scorable.jsonToMap(json) match {
      case None => None
      case Some(map) => {
        if (map contains "title") {
          val title = Scorable.getString(map, "title")
          val doi = Scorable.getString(map, "doi")
          val sha1 = Scorable.getString(map, "sha")
          // TODO: year, authors (if available)
          if (title == null || title.isEmpty) {
            None
          } else {
            val sf : ScorableFeatures = ScorableFeatures.create(title=title, doi=doi, sha1=sha1)
            sf.toSlug match {
              case None => None
              case Some(slug) => Some(MapFeatures(slug, sf.toString))
            }
          }
        } else {
          None
        }
      }
    }
  }
}
