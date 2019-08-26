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


class FatcatScorableRight extends Scorable {

  def getSource(args : Args) : Source = {
    TextLine(args("fatcat-release-input-right"))
  }

  def getFeaturesPipe(args : Args)(implicit mode : Mode, flowDef : FlowDef) : TypedPipe[Option[MapFeatures]] = {
    getSource(args).read
      .toTypedPipe[String](new Fields("line"))
      .filter { FatcatScorable.keepRecord(_) }
      .map { FatcatScorable.jsonToMapFeatures(_) }
  }
}

class FatcatScorable extends Scorable with HBasePipeConversions {

  def getSource(args : Args) : Source = {
    TextLine(args("fatcat-release-input"))
  }

  def getFeaturesPipe(args : Args)(implicit mode : Mode, flowDef : FlowDef) : TypedPipe[Option[MapFeatures]] = {
    getSource(args).read
      .toTypedPipe[String](new Fields("line"))
      .filter { FatcatScorable.keepRecord(_) }
      .map { FatcatScorable.jsonToMapFeatures(_) }
  }
}

object FatcatScorable {

  // Note; removed ReleaseType filtering

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
    def getTitle : Option[String] = {
      if (map contains "title") {
        val title = map("title").asInstanceOf[String]
        if (title == null || title.isEmpty) None else Some(title)
      } else {
        None
      }
    }

    def getSubtitle : Option[String] = {
      if (map contains "subtitle") {
        val subtitle = map("subtitle").asInstanceOf[String]
        if (subtitle == null || subtitle.isEmpty) {
          None
        } else {
          Some(subtitle)
        }
      } else {
        None
      }
    }

    getTitle match {
      case None => None
      case Some(baseTitle) => {
        if (baseTitle == null) {
          None
        } else {
          getSubtitle match {
            case None => Some(baseTitle)
            case Some(baseSubtitle) => Some(baseTitle.concat(":".concat(baseSubtitle)))
          }
        }
      }
    }
  }

  def mapToAuthorList(map : Map[String, Any]) : List[String] = {
    if (map contains "contribs") {
      val objArray = map("contribs").asInstanceOf[List[Any]].map(e => e.asInstanceOf[Map[String,Any]])
      // TODO(bnewbold): better name stuff... contrib.surname, creator.surname,
      // or raw_name split to last
      objArray
        .filter(e => e contains "raw_name")
        .map(e => e.get("raw_name").get.asInstanceOf[String])
    } else {
      List()
    }
  }

  def mapToYear(map : Map[String, Any]) : Option[Int] = {
    map.get("release_year") match {
      case None => None
      case Some(year) => {
        Some(year.asInstanceOf[Double].toInt)
      }
    }
  }

  def jsonToMapFeatures(json : String) : Option[MapFeatures] = {
    def makeMapFeatures(title : String, doi : String, fatcat_release: String, fatcat_work : String, authors : List[String], year : Int, contentType : String) : Option[MapFeatures] = {
      // NOTE: not doing any filtering here!
      val sf : ScorableFeatures = ScorableFeatures.create(title=title, authors=authors, doi=doi, fatcat_release=fatcat_release, fatcat_work=fatcat_work, year=year)
      sf.toSlug match {
        case None => None
        case Some(slug) => Some(MapFeatures(slug, sf.toString))
      }
    }
    Scorable.jsonToMap(json) match {
      case None => None
      case Some(map) =>
        mapToTitle(map) match {
          case None => None
          case Some(title) => makeMapFeatures(
            title=title,
            // TODO: doi=Scorable.getString(map, "doi"),
            doi=null,
            fatcat_release=Scorable.getString(map, "ident"),
            fatcat_work=Scorable.getString(map, "work_id"),
            authors=mapToAuthorList(map),
            year=mapToYear(map).getOrElse(0),
            contentType=map.get("type").map(e => e.asInstanceOf[String]).getOrElse("MISSING-CONTENT-TYPE"))
        }
    }
  }
}
