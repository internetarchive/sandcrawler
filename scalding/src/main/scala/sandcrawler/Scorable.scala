package sandcrawler

import scala.math
import scala.util.parsing.json.JSON
import scala.util.parsing.json.JSONObject

import cascading.flow.FlowDef
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
//import TDsl._

case class MapFeatures(slug : String, json : String)
case class ReduceFeatures(json : String)
case class ReduceOutput(val slug : String,  score : Int, json1 : String, json2 : String)

abstract class Scorable {
  def getInputPipe(args : Args)(implicit mode : Mode, flowDef : FlowDef) : TypedPipe[(String, ReduceFeatures)] =
  {
    getFeaturesPipe(args)
      .filter { entry => Scorable.isValidSlug(entry.slug) }
      .groupBy { case MapFeatures(slug, json) => slug }
      .map { tuple =>
        val (slug : String, features : MapFeatures) = tuple
        (slug, ReduceFeatures(features.json))
      }
  }

  // abstract methods
  def getSource(args : Args) : Source
  def getFeaturesPipe(args : Args)(implicit mode : Mode, flowDef : FlowDef) : TypedPipe[MapFeatures]
}

object Scorable {
  val NoSlug = "NO SLUG" // Used for slug if title is empty or unparseable

  def isValidSlug(slug : String) : Boolean = {
    slug != NoSlug
  }

  // NOTE: I could go all out and make ScorableMap a type.
  // TODO: Require year. Other features will get added here.
  def toScorableMap(title : String, year : Int = 0, doi : String = "", sha1 : String = "") : Map[String, Any] = {
   Map("title" -> title, "year" -> year, "doi" -> doi, "sha1" -> sha1)
  }

  def toScorableJson(title : String, year : Int, doi : String = "", sha1 : String = "") : String = {
    JSONObject(toScorableMap(title=title, year=year, doi=doi, sha1=sha1)).toString
  }

  // TODO: Score on more fields than "title".
  def isScorableMap(map : Map[String, Any]) : Boolean = {
    map.contains("title")
  }

  def jsonToMap(json : String) : Option[Map[String, Any]] = {
    // https://stackoverflow.com/a/32717262/631051
    val jsonObject = JSON.parseFull(json)
    if (jsonObject == None) {
      None
    } else {
      Some(jsonObject.get.asInstanceOf[Map[String, Any]])
    }
  }

  // Map should have been produced by toScorableMap.
  // This guarantees it will have all of the fields needed to compute
  // the ultimate score, which are a superset of those needed for a slug.
  def mapToSlug(map : Map[String, Any]) : String = {
    val unaccented = StringUtilities.removeAccents(getString(map, "title"))
    // Remove punctuation after splitting on colon.
    val slug = StringUtilities.removePunctuation((unaccented.split(":")(0).toLowerCase()))
    if (slug.isEmpty || slug == null) {
      NoSlug
    } else {
      slug
    }
  }

  def getStringOption(optionalMap : Option[Map[String, Any]], key : String) : Option[String] = {
    optionalMap match {
      case None => None
      case Some(map) => if (map contains key) Some(map(key).asInstanceOf[String]) else None
    }
  }

  // Caller is responsible for ensuring that key is a String in map.
  // TODO: Add and handle ClassCastException
  def getString(map : Map[String, Any], key : String) : String = {
    assert(map contains key)
    map(key).asInstanceOf[String]
  }

  val MaxScore = 1000

  def computeSimilarity(features1 : ReduceFeatures, features2 : ReduceFeatures) : Int = {
    val json1 = jsonToMap(features1.json)
    val json2 = jsonToMap(features2.json)
    getStringOption(json1, "title") match {
      case None => 0
      case Some(title1) => {
        getStringOption(json2, "title") match {
          case None => 0
          case Some(title2) =>
            (StringUtilities.similarity(title1, title2) * MaxScore).toInt
        }
      }
    }
  }
}
