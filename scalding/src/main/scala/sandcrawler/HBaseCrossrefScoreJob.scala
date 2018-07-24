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
  def grobidToSlug(json : String) : Option[String] = {
    // https://stackoverflow.com/a/32717262/631051
    val jsonObject = JSON.parseFull(json)
    if (jsonObject == None) {
      None
    } else {
      val globalMap = jsonObject.get.asInstanceOf[Map[String, Any]]
      globalMap.get("title") match {
        case Some(title) => Some(titleToSlug(title.asInstanceOf[String]))
        case None => None
      }
    }
  }

  def crossrefToSlug(json : String) : Option[String] = {
    val jsonObject = JSON.parseFull(json)
    if (jsonObject == None) {
      None
    } else {
      val globalMap = jsonObject.get.asInstanceOf[Map[String, Any]]
      globalMap.get("title") match {
        case Some(title) => Some(titleToSlug(title.asInstanceOf[List[String]](0)))
        case None => None
      }
    }
  }

  def titleToSlug(title : String) : String = {
    title.split(":")(0).toLowerCase()
  }
}
