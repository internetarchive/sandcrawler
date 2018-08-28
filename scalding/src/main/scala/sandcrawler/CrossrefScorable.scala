package sandcrawler

import scala.math
import scala.util.parsing.json.JSON
import scala.util.parsing.json.JSONArray
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

  def getFeaturesPipe(args : Args)(implicit mode : Mode, flowDef : FlowDef) : TypedPipe[Option[MapFeatures]] = {
    getSource(args).read
      .toTypedPipe[String](new Fields("line"))
      .filter { CrossrefScorable.keepRecord(_) }
      .map { CrossrefScorable.jsonToMapFeatures(_) }
  }
}

object CrossrefScorable {

  val ContentTypeWhitelist: Set[String] = Set(
    "book",
    "book-chapter",
    "dataset",
    "dissertation",
    "journal-article",
    "letter",
    "monograph",
    "posted-content",
    "pre-print",
    "proceedings-article",
    "report",
    "working-paper")

  def keepRecord(json : String) : Boolean = {
    Scorable.jsonToMap(json) match {
      case None => false
      case Some(map) => {
        mapToTitle(map) match {
          case None => false
          case Some(title) => title.length <= Scorable.MaxTitleLength
        }
      }
    }
  }

  // Returns None if title is null, empty, or too long.
  def mapToTitle(map : Map[String, Any]) : Option[String] = {
    if (map contains "title") {
      val titles = map("title").asInstanceOf[List[String]]
      if (titles.isEmpty || titles == null) {
        None
      } else {
        val baseTitle: String = titles(0)
        // TODO(bnewbold): this code block is horrible
        val baseSubtitle: String = if (map contains "subtitle") {
          val subtitles = map("subtitle").asInstanceOf[List[String]]
          if (!subtitles.isEmpty && subtitles != null) {
            val sub = subtitles(0)
            if (sub != null && !sub.isEmpty && baseTitle != null) {
              sub
            } else {
              ""
            }
          } else {
            ""
          }
        } else {
          ""
        }
        val title = if (baseSubtitle.isEmpty) {
          baseTitle
        } else {
          baseTitle.concat(": ".concat(baseSubtitle))
        }
        if (title == null || title.isEmpty || title.length > Scorable.MaxTitleLength) None else Some(title)
      }
    } else {
      None
    }
  }

  def mapToAuthorList(map : Map[String, Any]) : List[String] = {
    if (map contains "author") {
      val objArray = map("author").asInstanceOf[List[Any]].map(e => e.asInstanceOf[Map[String,Any]])
      // TODO(bnewbold): combine given and family names?
      objArray
        .filter(e => e contains "family")
        .map(e => e.get("family").get.asInstanceOf[String])
    } else {
      List()
    }
  }

  def mapToYear(map : Map[String, Any]) : Option[Int] = {
    map.get("created") match {
      case None => None
      case Some(created) => {
        Some(created.asInstanceOf[Map[String,Any]]
                    .get("date-parts")
                    .get
                    .asInstanceOf[List[Any]](0)
                    .asInstanceOf[List[Any]](0)
                    .asInstanceOf[Double]
                    .toInt)
      }
    }
  }

  def jsonToMapFeatures(json : String) : Option[MapFeatures] = {
    Scorable.jsonToMap(json) match {
      case None => None
      case Some(map) =>
        mapToTitle(map) match {
          case None => None
          case Some(title) => {
            val doi = Scorable.getString(map, "DOI")
            val authors: List[String] = mapToAuthorList(map)
            val year: Int = mapToYear(map).getOrElse(0)
            val contentType: String = map.get("type").map(e => e.asInstanceOf[String]).getOrElse("MISSING-CONTENT-TYPE")
            if (doi.isEmpty || doi == null || authors.length == 0 || !(ContentTypeWhitelist contains contentType)) {
              None
            } else {
              val sf : ScorableFeatures = ScorableFeatures.create(title=title, authors=authors, doi=doi.toLowerCase(), year=year)
              sf.toSlug match {
                case None => None
                case Some(slug) => Some(MapFeatures(slug, sf.toString))
              }
            }
          }
        }
    }
  }
}
