package sandcrawler

import java.util.Arrays
import java.util.Properties

import scala.math
import scala.util.parsing.json.JSON

import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.CoGrouped
import com.twitter.scalding.typed.Grouped
import com.twitter.scalding.typed.TDsl._
import org.apache.hadoop.hbase.io.ImmutableBytesWritable
import org.apache.hadoop.hbase.util.Bytes
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource

class HBaseCrossrefScoreJob(args: Args) extends JobBase(args) with HBasePipeConversions {
  val NoTitle = "NO TITLE" // Used for slug if title is empty or unparseable

  // key is SHA1
  val grobidSource = HBaseCrossrefScore.getHBaseSource(
    args("hbase-table"),
    args("zookeeper-hosts"))
  val grobidPipe : TypedPipe[(String, String, String)] = grobidSource
    .read
    .fromBytesWritable(new Fields("key", "tei_json"))
    //  .debug  // Should be 4 tuples for mocked data
    .toTypedPipe[(String, String)]('key, 'tei_json)
    .map { entry =>
      val (key, json) = (entry._1, entry._2)
      // TODO: Consider passing forward only a subset of JSON.
      HBaseCrossrefScore.grobidToSlug(json) match {
        case Some(slug) => (slug, key, json)
        case None => (NoTitle, key, json)
      }
    }
    .filter { entry =>
      val (slug, _, _) = entry
      slug != NoTitle
    }
    .debug  // SHould be 3 tuples for mocked data

  val grobidGroup = grobidPipe
    .groupBy { case (slug, key, json) => slug }

  val crossrefSource = TextLine(args("crossref-input"))
  val crossrefPipe : TypedPipe[(String, String)] = crossrefSource
    .read
    //    .debug // Should be 4 tuples for mocked data
    .toTypedPipe[String]('line)
    .map{ json : String =>
      HBaseCrossrefScore.crossrefToSlug(json) match {
        case Some(slug) => (slug, json)
        case None => (NoTitle, json)
      }
    }
    .filter { entry =>
      val (slug, json) = entry
      slug != NoTitle
    }

  val crossrefGroup = crossrefPipe
  .groupBy { case (slug, json) => slug }

  val theJoin : CoGrouped[String, ((String, String, String), (String, String))] =
    grobidGroup.join(crossrefGroup)

  theJoin.map{ entry =>
    val (slug : String,
      ((slug0: String, sha1 : String, grobidJson : String),
        (slug1 : String, crossrefJson : String))) = entry
    HBaseCrossrefScore.computeOutput(sha1, grobidJson, crossrefJson)}
    .debug
  // Output: score, sha1, doi, grobid title, crossref title
    .write(TypedTsv[(Int, String, String, String, String)](args("output")))

}

object HBaseCrossrefScore {
  def getHBaseSource(hbaseTable: String, zookeeperHosts: String) : HBaseSource = HBaseBuilder.build(
    hbaseTable,      // HBase Table Name
    zookeeperHosts,  // HBase Zookeeper server (to get runtime config info; can be array?)
    List("grobid0:tei_json"),
    SourceMode.SCAN_ALL)

  def performJoin(grobidJson : String, crossRefJson : String, sha1 : String) : (String, String, String) = {
    (sha1, "1.2.3.4", "100")
  }

  def jsonToMap(json : String) : Map[String, Any] = {
    // https://stackoverflow.com/a/32717262/631051
    val jsonObject = JSON.parseFull(json)
    if (jsonObject == None) {
      // Empty map for malformed JSON
      Map[String, Any]("malformed json" -> json)
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
      // TODO: Don't ignore titles after the first.
      titleToSlug(map("title").asInstanceOf[List[String]](0))
    } else {
      Some(map.keys.mkString(","))
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

  val FullTitleMatch = 100
  val TitleLeftMatchBase = 50
  val MaxTitleLeftMatch = 80
  val SlugMatch = 25

  def computeSimilarity(gTitle : String, cTitle : String) : Int = {
    assert(titleToSlug(gTitle) == titleToSlug(cTitle))
    if (gTitle == cTitle) {
      FullTitleMatch
    } else if (gTitle.startsWith(cTitle) || cTitle.startsWith(gTitle)) {
      math.min(TitleLeftMatchBase + math.abs(gTitle.length - cTitle.length),
        MaxTitleLeftMatch)
    } else {
      SlugMatch
    }
  }

  def computeOutput(sha1 : String, grobidJson : String, crossrefJson : String) :
    // (score, sha1, doi, grobidTitle, crossrefTitle)
      (Int, String, String, String, String) = {
    // JSON has already been validated in previous stages.
    val grobid = jsonToMap(grobidJson)
    val crossref = jsonToMap(crossrefJson)

    val grobidTitle = grobid("title").asInstanceOf[String].toLowerCase()
    val crossrefTitle = crossref("title").asInstanceOf[List[String]](0).toLowerCase()
    (computeSimilarity(grobidTitle, crossrefTitle),
      sha1,
      crossref("DOI").asInstanceOf[String],
      "'" + grobidTitle + "'",
      "'" + crossrefTitle + "'")
  }
}
