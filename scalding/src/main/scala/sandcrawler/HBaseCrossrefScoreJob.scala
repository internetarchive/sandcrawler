package sandcrawler

import java.util.Properties

import scala.util.parsing.json.JSON

import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import org.apache.hadoop.hbase.io.ImmutableBytesWritable
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions

class HBaseCrossrefScoreJob(args: Args) extends JobBase(args) with HBasePipeConversions {

  // key is SHA1
  val grobidSource = HBaseBuilder.build(
    args("grobid-table"),
    args("zookeeper-hosts"),
    List("grobid0:tei_json"),
    sourceMode = SourceMode.SCAN_ALL)

  val grobidPipe = grobidSource
    .read
    .map('tei_json -> 'slug) {
      json : String => HBaseCrossrefScore.grobidToSlug(json)}

  val crossrefSource = TextLine(args("input"))
  val crossrefPipe = crossrefSource
    .read
    .map('line -> 'slug) {
      json : String => HBaseCrossrefScore.crossrefToSlug(json)}

/*
  statusPipe.groupBy { identity }
    .size
    .debug
    .write(TypedTsv[(Long,Long)](args("output")))
   */
}

object HBaseCrossrefScore {
  def jsonToMap(json : String) : Map[String, Any] = {
    // https://stackoverflow.com/a/32717262/631051
    val jsonObject = JSON.parseFull(json)
    if (jsonObject == None) {
      // Empty map for malformed JSON
      Map[String, Any]()
    } else {
      jsonObject.get.asInstanceOf[Map[String, Any]]
    }
  }


  def grobidToSlug(json : String) : Option[String] = {
    val map = jsonToMap(json)
    if (map contains "title") {
      titleToSlug(map("title").asInstanceOf[String])
    } else {
      None
    }
  }

  def crossrefToSlug(json : String) : Option[String] = {
    val map = jsonToMap(json)
    if (map contains "title") {
      titleToSlug(map("title").asInstanceOf[List[String]](0))
    } else {
      None
    }
  }

  def titleToSlug(title : String) : Option[String] = {
    val slug = title.split(":")(0).toLowerCase()
    if (slug.isEmpty) {
      None
    } else {
      Some(slug)
    }
  }
}
