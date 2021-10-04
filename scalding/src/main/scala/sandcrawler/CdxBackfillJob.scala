package sandcrawler

import java.util.Properties

import scala.util.Try
import scala.util.matching.Regex
import scala.util.parsing.json.JSONObject

import cascading.pipe.joiner._
import cascading.property.AppProps
import cascading.tap.SinkMode
import cascading.tuple.Fields
import com.twitter.scalding._
import com.twitter.scalding.typed.TDsl._
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBasePipeConversions
import parallelai.spyglass.hbase.HBaseSource

// Type that represents a raw parsed CDX line
case class CdxLine(surt: String, datetime: String, url: String, mime: String, httpStatus: String, sha1: String, c_size: String, offset: String, warc: String)

/**
 *  CDX backfill:
 *  1. parse CDX (all columns)
 *  2. filter CDX (pdf, HTTP 200, etc)
 *  3. source HBase (key column only)
 *  4. left join CDX to HBase
 *  5. filter to only those with null HBase key column
 *  6. convert CDX fields to HBase columns
 *  7. sink results to HBase
 */
class CdxBackfillJob(args: Args) extends JobBase(args) with HBasePipeConversions {

  import CdxBackfillJob._

  val hbaseSource = getHBaseSource(args("hbase-table"), args("zookeeper-hosts"))
  val hbaseSink = getHBaseSink(args("hbase-table"), args("zookeeper-hosts"))

  // Parse CDX lines from text file to typed pipe
  val lines : TypedPipe[String] = TypedPipe.from(TextLine(args("cdx-input-path")))

  val cdxLines : TypedPipe[CdxLine] = lines
    .filter { isCdxLine }
    .map { lineToCdxLine }
    .filter { CdxBackfillJob.keepCdx(_) }

  // (key, f:c, file:cdx, file:mime)
  val cdxRows : TypedPipe[(String, String, String, String)] = cdxLines
    .map { CdxBackfillJob.cdxLineToRow }
    .debug

  val existingKeys : TypedPipe[String] = hbaseSource
    .read
    .fromBytesWritable( new Fields("key") )
    .toTypedPipe[String]('key)
    //.debug

  // filters out all the lines that have an existing SHA1 key in HBase
  // the groupBy statements are to select key values to join on.
  // (key, f:c, file:cdx, file:mime)
  val newRows : TypedPipe[(String, String, String, String)] = existingKeys
    .groupBy( identity )
    .rightJoin(cdxRows.groupBy(_._1))
    .toTypedPipe
    .collect { case (_, (None, row)) => row }
    .debug

  // convert to tuple form and write out into HBase
  newRows
    .toPipe('key, 'c, 'cdx, 'mime)
    .toBytesWritable( new Fields("key", "c", "cdx", "mime") )
    .write(hbaseSink)

}

object CdxBackfillJob {

  def getHBaseSource(hbase_table: String, zookeeper_hosts: String) : HBaseSource = {
    HBaseBuilder.build(
      hbase_table,
      zookeeper_hosts,
      List("file:size"), // not actually needed
      SourceMode.SCAN_ALL)
  }

  def getHBaseSink(hbase_table: String, zookeeper_hosts: String) : HBaseSource = {
    HBaseBuilder.buildSink(
      hbase_table,
      zookeeper_hosts,
      List("f:c", "file:cdx", "file:mime"),
      SinkMode.UPDATE)
  }

  def normalizeMime(raw: String) : String = {

    val normalMime = Map(
      "application/pdf" -> "application/pdf",
      "application/x-pdf" -> "application/pdf",
      "('application/pdf'" -> "application/pdf",
      "image/pdf" -> "application/pdf",
      "text/pdf" -> "application/pdf",
      "\"application/pdf\"" -> "application/pdf",
      "application/postscript" -> "application/postscript",
      "text/html" -> "text/html",
      "text/xml" -> "text/xml",
      "application/xml" -> "text/xml"
    )

    val lower = raw.toLowerCase()
    normalMime.find { case (key, _) =>
      lower.startsWith(key)
    } match {
      case Some((_, value)) => value
      case None => lower
    }
  }

  def isCdxLine(line: String) : Boolean = {
    // malformatted or non-CDX11 lines
    !(line.startsWith("#") || line.startsWith(" ") || line.startsWith("filedesc") ||
      line.split(" ").size != 11)
  }

  def keepCdx(line: CdxLine) : Boolean = {
    val sha1Pattern = """[A-Z2-7]{32}""".r
    if (List(line.surt, line.datetime, line.url, line.mime, line.c_size, line.offset, line.warc).contains("-")) {
      false
    } else if (line.httpStatus != "200") {
      false
    } else if (line.mime != "application/pdf") {
      false
    } else if (sha1Pattern.unapplySeq(line.sha1).isEmpty) {
      false
    } else if (List(line.c_size, line.offset, line.datetime).map(s => Try(s.toLong).toOption).contains(None)) {
      false
    } else {
      true
    }
  }

  // Returns (key, f:c, file:cdx, file:mime), all as strings, which is close to
  // how they will be inserted into HBase
  def cdxLineToRow(line: CdxLine) : (String, String, String, String) = {

    val key = "sha1:" + line.sha1

    val warcFile = line.warc.split('/')(1)

    // Read CDX-style datetime and conver to ISO 8601 with second resolution
    val dtFormat = new java.text.SimpleDateFormat("yyyyMMddHHmmss")
    val isoFormat = new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'")
    // TODO: timezones? UTC to UTC, so I don't think so.
    val dtIso = isoFormat.format(dtFormat.parse(line.datetime))

    // This is the "f:c" field. 'i' intentionally not set
    // python: f:c = dict(u=url, d=dt_iso, f=warc_file, o=int(offset), c=1)
    // python: warc_file = warc.split('/')[-1]
    // python: dt_iso = datetime.strptime(dt, "%Y%m%d%H%M%S").isoformat()
    val heritrixInfo = JSONObject(Map(
      "u" -> line.url,
      "d" -> dtIso,
      "f" -> warcFile,
      "o" -> line.offset.toInt,
      "c" -> line.c_size.toInt
    ))

    // python: dict(surt=surt, dt=dt, url=url, c_size=int(c_size),
    //                 offset=int(offset), warc=warc)
    val fileCdx = JSONObject(Map(
      "surt" -> line.surt,
      "dt" -> line.datetime,
      "url" -> line.url,
      "c_size" -> line.c_size.toInt,
      "offset" -> line.offset.toInt,
      "warc" -> line.warc
    ))
    (key, heritrixInfo.toString(), fileCdx.toString(), normalizeMime(line.mime))
  }

  def lineToCdxLine(line: String) : CdxLine = {
    val raw = line.split("\\s+")
    // surt, datetime, url, mime, http_status, sha1, SKIP, SKIP, c_size, offset, warc
    CdxLine(raw(0), raw(1), raw(2), raw(3), raw(4), raw(5), raw(8), raw(9), raw(10))
  }

}
