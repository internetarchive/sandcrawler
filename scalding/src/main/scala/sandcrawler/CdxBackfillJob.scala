package sandcrawler

import cascading.property.AppProps
import cascading.tuple.Fields
import cascading.pipe.joiner._
import com.twitter.scalding._
import java.util.Properties
import parallelai.spyglass.base.JobBase
import parallelai.spyglass.hbase.{HBaseSource, HBasePipeConversions}
import parallelai.spyglass.hbase.HBaseConstants.SourceMode

// Type that represents a raw parsed CDX line
case class CdxLine(surt: String, datetime: String, url: String, mime: String, http_status: String, sha1: String, c_size: String, offset: String, warc: String)

/**
 *  CDX backfill:
 *  1. parse CDX (all columns)
 *  2. filter CDX (pdf, HTTP 200, etc)
 *  3. source HBase (key column only)
 *  4. left join CDX to HBase
 *  5. filter to only those with null HBase key column
 *  6. convert CDX fields to HBase columns
 *  7. sink results to HBase
 *
 * TODO: I really mixed the Scalding "field-base" and "type-based" APIs here.
 * Should decide on a best practice.
 */
class CdxBackfillJob(args: Args) extends JobBase(args) with HBasePipeConversions {

  //import CdxLine._
  // XXX remove all other CdxBackfillJob.whatever
  import CdxBackfillJob._

  val cdxInputPath = args("cdx-input-path")
  val hbaseTable = args("hbase-table")
  val zookeeperHosts = args("zookeeper-hosts")

  val hbaseSource = getHBaseSource(args("hbase-table"), args("zookeeper-hosts"))

  val lines : TypedPipe[String] = TypedPipe.from(TextLine(cdxInputPath))

  val cdxLines : TypedPipe[CdxLine] = lines
    .filter { isCdxLine }
    .map { lineToCdxLine }
    .filter { CdxBackfillJob.keepCdx(_) }

  val cdxRows = cdxLines
    .map { CdxBackfillJob.cdxLineToRow(_) }
    .toPipe(('key, 'f_c, 'file_cdx, 'file_mime))

  val hbaseKeys = hbaseSource
    .project('key)
    .mapTo('key -> 'existingKey) { key : String => key }

  // filters out all the lines that have an existing SHA1 key in HBase
  val newRows = cdxRows
    .joinWithLarger('key -> 'existingKey, hbaseKeys, joiner = new LeftJoin)
    .filter('existingKey) { k : String => k == null } // is String the right type?

  newRows
    .write(hbaseSource)

}

object CdxBackfillJob {

  def getHBaseSource(hbase_table: String, zookeeper_hosts: String) : HBaseSource = {
    return HBaseBuilder.build(
      hbase_table,
      zookeeper_hosts,
      List("file:size"), // not actually needed
      SourceMode.SCAN_ALL)
  }

  def normalizeMime(raw: String) : String = {

    val NORMAL_MIME = List("application/pdf",
                           "application/postscript",
                           "text/html",
                           "text/xml")

    val lower = raw.toLowerCase()
    NORMAL_MIME.foreach(norm =>
      if (lower.startsWith(norm)) {
        return norm
      }
    )

    // Common special cases
    if (lower.startsWith("application/xml")) {
      return "text/xml"
    }
    if (lower.startsWith("application/x-pdf")) {
      return "application/pdf"
    }
    return lower

  }

  def isCdxLine(line: String) : Boolean = {
    // malformated or non-CDX11 lines
    !(line.startsWith("#") || line.startsWith(" ") || line.startsWith("filedesc") ||
      line.split(" ").size != 11)
  }

  def keepCdx(line: CdxLine) : Boolean = {
    // TODO: sha1.isalnum() and c_size.isdigit() and offset.isdigit() and dt.isdigit()
    if (line.http_status != "200" || line.sha1.size != 32) {
      return false
    }
    // TODO: '-' in (line.surt, line.datetime, line.url, line.mime, line.c_size, line.offset, line.warc)
    return true
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

    // warc_file = warc.split('/')[-1]
    // dt_iso = datetime.strptime(dt, "%Y%m%d%H%M%S").isoformat()
    // f:c = dict(u=url, d=dt_iso, f=warc_file, o=int(offset), c=1)

    // This is the "f:c" field. 'i' intentionally not set
    val heritrixInfo = ""

    // file:cdx = dict(surt=surt, dt=dt, url=url, c_size=int(c_size),
    //                 offset=int(offset), warc=warc)
    val fileCdx = ""
    (key, heritrixInfo, fileCdx, line.mime)
  }

  def lineToCdxLine(line: String) : CdxLine = {
    val raw = line.split("\\s+")
    // surt, datetime, url, mime, http_status, sha1, SKIP, SKIP, c_size, offset, warc
    CdxLine(raw(0), raw(1), raw(2), raw(3), raw(4), raw(5), raw(8), raw(9), raw(10))
  }

}
