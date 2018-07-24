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

  /*
  val crossrefSource = TextLine(args("input"))
  val crossrefPipe = crossrefSource
    .read
    .map('line -> 'slug) {
      json : String => crossrefToSlug(json)}


  statusPipe.groupBy { identity }
    .size
    .debug
    .write(TypedTsv[(Long,Long)](args("output")))
   */
}

object HBaseCrossrefScore {
  def grobidToSlug(json : String) = {
    // https://stackoverflow.com/a/32717262/631051
    val jsonObject = JSON.parseFull(json)
    val globalMap = jsonObject.get.asInstanceOf[Map[String, Any]]
    globalMap.get("title") match {
      case Some(title) => titleToSlug(title.asInstanceOf[String])
      case None => ""
    }
  }

  def titleToSlug(title : String) = {
    title.split(":")(0)
  }
}
