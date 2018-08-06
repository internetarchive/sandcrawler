package sandcrawler

import java.text.Normalizer
import java.util.Arrays
import java.util.Properties
import java.util.regex.Pattern

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

  val pipe0 : cascading.pipe.Pipe = grobidSource.read
  val grobidPipe : TypedPipe[(String, String, String)] = pipe0
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
//    .debug  // SHould be 3 tuples for mocked data

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
    // Output: score, sha1, doi, grobid title, crossref title
    .write(TypedTsv[(Int, String, String, String, String)](args("output")))
}

object HBaseCrossrefScore {
  def getHBaseSource(hbaseTable: String, zookeeperHosts: String) : HBaseSource = HBaseBuilder.build(
    hbaseTable,      // HBase Table Name
    zookeeperHosts,  // HBase Zookeeper server (to get runtime config info; can be array?)
    List("grobid0:tei_json"),
    SourceMode.SCAN_ALL)

  def jsonToMap(json : String) : Option[Map[String, Any]] = {
    // https://stackoverflow.com/a/32717262/631051
    val jsonObject = JSON.parseFull(json)
    if (jsonObject == None) {
      None
    } else {
      Some(jsonObject.get.asInstanceOf[Map[String, Any]])
    }
  }

  def grobidToSlug(json : String) : Option[String] = {
    jsonToMap(json) match {
      case None => None
      case Some(map) => {
        if (map contains "title") {
          titleToSlug(map("title").asInstanceOf[String])
        } else {
          None
        }
      }
    }
  }

  def crossrefToSlug(json : String) : Option[String] = {
    jsonToMap(json) match {
      case None => None
      case Some(map) => {
        if (map contains "title") {
          // TODO: Don't ignore titles after the first.
          titleToSlug(map("title").asInstanceOf[List[String]](0))
        } else {
          None
        }
      }
    }
  }

  def titleToSlug(title : String) : Option[String] = {
    val slug = removeAccents(title).split(":")(0).toLowerCase()
    if (slug.isEmpty) {
      None
    } else {
      Some(slug)
    }
  }

  val MaxScore = 1000

  def computeOutput(sha1 : String, grobidJson : String, crossrefJson : String) :
    // (score, sha1, doi, grobidTitle, crossrefTitle)
      (Int, String, String, String, String) = {
    jsonToMap(grobidJson) match {
      case None => (0, "", "", "", "")  // This can't happen, because grobidJson already validated in earlier stage
      case Some(grobid) => {
        val grobidTitle = grobid("title").asInstanceOf[String].toLowerCase()

        jsonToMap(crossrefJson) match {
          case None => (0, "", "", "", "")  // This can't happen, because crossrefJson already validated in earlier stage
          case Some(crossref) => {
            val crossrefTitle = crossref("title").asInstanceOf[List[String]](0).toLowerCase()

            (similarity(removeAccents(grobidTitle), removeAccents(crossrefTitle)),
              sha1,
              crossref("DOI").asInstanceOf[String],
              "'" + grobidTitle + "'",
              "'" + crossrefTitle + "'")
          }
        }
      }
    }
  }

  // Adapted from https://git-wip-us.apache.org/repos/asf?p=commons-lang.git;a=blob;f=src/main/java/org/apache/commons/lang3/StringUtils.java;h=1d7b9b99335865a88c509339f700ce71ce2c71f2;hb=HEAD#l934
  def removeAccents(s : String) : String = {
    val replacements = Map(
      '\u0141' -> 'L',
      '\u0142' -> 'l',  // Letter ell
      '\u00d8' -> 'O',
      '\u00f8' -> 'o'
    )
    val sb = new StringBuilder(Normalizer.normalize(s, Normalizer.Form.NFD))
    for (i <- 0 to sb.length - 1) {
      for (key <- replacements.keys) {
        if (sb(i) == key) {
          sb.deleteCharAt(i);
          sb.insert(i, replacements(key))
        }
      }
    }
    val pattern = Pattern.compile("\\p{InCombiningDiacriticalMarks}+")
    pattern.matcher(sb).replaceAll("")
  }

  // Adapted from: https://stackoverflow.com/a/16018452/631051
  def similarity(s1 : String, s2 : String) : Int = {
    val longer : String = if (s1.length > s2.length) s1 else s2
    val shorter : String = if (s1.length > s2.length) s2 else s1
    if (longer.length == 0) {
      // Both strings are empty.
      MaxScore
    } else {
      (longer.length - stringDistance(longer, shorter)) * MaxScore / longer.length
    }
  }

  // Source: // https://oldfashionedsoftware.com/2009/11/19/string-distance-and-refactoring-in-scala/
  def stringDistance(s1: String, s2: String): Int = {
    val memo = scala.collection.mutable.Map[(List[Char],List[Char]),Int]()
    def min(a:Int, b:Int, c:Int) = Math.min( Math.min( a, b ), c)
    def sd(s1: List[Char], s2: List[Char]): Int = {
      if (!memo.contains((s1, s2))) {
        memo((s1,s2)) = (s1, s2) match {
          case (_, Nil) => s1.length
          case (Nil, _) => s2.length
          case (c1::t1, c2::t2)  =>
            min( sd(t1,s2) + 1, sd(s1,t2) + 1,
              sd(t1,t2) + (if (c1==c2) 0 else 1) )
        }
      }
      memo((s1,s2))
    }

    sd( s1.toList, s2.toList )
  }
}

