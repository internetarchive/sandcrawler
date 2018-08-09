package sandcrawler

import scala.math
import scala.util.parsing.json.JSON

import cascading.flow.FlowDef
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._

case class MapFeatures(slug : String, json : String)
case class ReduceFeatures(json : String)
case class ReduceOutput(val score : Int, json1 : String, json2 : String)

abstract class Scorable {
  def getInputPipe(args : Args, flowDef : FlowDef, mode : Mode) : TypedPipe[(String, ReduceFeatures)] =
  {
    getFeaturesPipe(args)(flowDef, mode)
      .filter { entry => Scorable.isValidSlug(entry.slug) }
      .groupBy { case MapFeatures(slug, json) => slug }
      .map { tuple =>
        val (slug : String, features : MapFeatures) = tuple
        (slug, ReduceFeatures(features.json))
      }
  }

  // abstract method
  def getFeaturesPipe(args : Args)(implicit flowDef : FlowDef, mode : Mode) : TypedPipe[MapFeatures]
}

object Scorable {
  val NoSlug = "NO SLUG" // Used for slug if title is empty or unparseable

  def isValidSlug(slug : String) = {
    slug != NoSlug
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

  def titleToSlug(title : String) : String = {
    if (title == null || title.isEmpty) {
      NoSlug
    } else {
      val unaccented = StringUtilities.removeAccents(title)
      // Remove punctuation after splitting on colon.
      val slug = StringUtilities.removePunctuation((unaccented.split(":")(0).toLowerCase()))
      if (slug.isEmpty || slug == null) {
        NoSlug
      } else {
        slug
      }
    }
  }

  def getStringOption(optionalMap : Option[Map[String, Any]], key : String) 
      : Option[String] = {
    optionalMap match {
      case None => None
      case Some(map) => if (map contains key) Some(map(key).asInstanceOf[String]) else None
    }
  }

  // Caller is responsible for ensuring that key is in map.
  def getString(map : Map[String, String], key : String) : String = {
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
