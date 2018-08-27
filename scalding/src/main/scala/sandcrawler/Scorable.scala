package sandcrawler

import scala.math
import scala.util.parsing.json.JSON
import scala.util.parsing.json.JSONObject

import cascading.flow.FlowDef
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._

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
  val MaxTitleLength = 1023
  val NoSlug = "NO SLUG" // Used for slug if title is empty or unparseable

  def isValidSlug(slug : String) : Boolean = {
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
            (StringUtilities.similarity(title1.toLowerCase, title2.toLowerCase) * MaxScore).toInt
        }
      }
    }
  }
}
