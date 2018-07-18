
package sandcrawler

import org.scalatest._
import cascading.tuple.{Tuple, Fields}
import com.twitter.scalding.{JobTest, Tsv, TypedTsv, TupleConversions, TextLine}
import org.apache.hadoop.hbase.io.ImmutableBytesWritable
import org.apache.hadoop.hbase.util.Bytes
import org.junit.runner.RunWith
import org.scalatest.FunSpec
import org.scalatest.junit.JUnitRunner
import org.slf4j.LoggerFactory
import parallelai.spyglass.hbase.HBaseSource
import parallelai.spyglass.hbase.HBaseConstants.SourceMode

class CdxBackfillTest extends FlatSpec with Matchers {

  import CdxBackfillJob._

  it should "normalize mimetypes" in {
    assert(CdxBackfillJob.normalizeMime("asdf") === "asdf")
    assert(CdxBackfillJob.normalizeMime("application/pdf") === "application/pdf")
    assert(CdxBackfillJob.normalizeMime("application/pdf+journal") === "application/pdf")
    assert(CdxBackfillJob.normalizeMime("Application/PDF") === "application/pdf")
    assert(CdxBackfillJob.normalizeMime("application/p") === "application/p")
    assert(CdxBackfillJob.normalizeMime("application/xml+stuff") === "text/xml")
    assert(CdxBackfillJob.normalizeMime("application/x-pdf") === "application/pdf")
    assert(CdxBackfillJob.normalizeMime("application/x-html") === "application/x-html")
  }

  it should "filter CDX lines" in {
    assert(true === keepCdx(lineToCdxLine(
      "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz")))
    // redirect
    assert(false === keepCdx(lineToCdxLine(
      "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 301 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz")))
  }

  it should "know what CDX lines are" in {
    assert(true === isCdxLine(
      "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz"))
    assert(false === isCdxLine(""))
    assert(false === isCdxLine(
      " edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz"))
    assert(false === isCdxLine(
      "#edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz"))
    // missing two fields
    assert(false === isCdxLine(
      "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz"))
    // extra field
    assert(false === isCdxLine(
      "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz -"))
  }

  it should "execute lineToRow" in {
    cdxLineToRow(lineToCdxLine(
      "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz"))
  }

}

@RunWith(classOf[JUnitRunner])
class CdxBackfillJobTest extends FunSpec with TupleConversions {

  val output = "/tmp/testOutput"
  val (testTable, testHost, testCdxFile) = ("test-table", "dummy-host:2181", "test_file.cdx")

  val log = LoggerFactory.getLogger(this.getClass.getName)

  val dummySizeBytes = Bytes.toBytes(100)

  val sampleData = List(
    List(Bytes.toBytes("sha1:K2DKSSVTXWPRMFDTWSTCQW3RVWRIOV3Q"), dummySizeBytes),
    List(Bytes.toBytes("sha1:C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ3WU"), dummySizeBytes),
    List(Bytes.toBytes("sha1:SDKUVHC3YNNEGH5WAG5ZAAXWAEBNX4WT"), dummySizeBytes),
    List(Bytes.toBytes("sha1:095893C3YNNEGH5WAG5ZAAXWAEBNXJWT"), dummySizeBytes)
  )
  val sampleCdxLines = List(
    // clean line
    "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz",
    // has existing SHA1
    "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ3WU - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz",
    // HTTP status code
    "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 301 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz",
    // not CDX (prefixed with hash)
    "#edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz"
  )

  JobTest("sandcrawler.CdxBackfillJob")
    .arg("test", "")
    .arg("app.conf.path", "app.conf")
    .arg("output", output)
    .arg("hbase-table", testTable)
    .arg("zookeeper-hosts", testHost)
    .arg("cdx-input-path", testCdxFile)
    .arg("debug", "true")
    .source[Tuple](CdxBackfillJob.getHBaseSource(testTable, testHost),
      sampleData.map(l => new Tuple(l.map(s => {new ImmutableBytesWritable(s)}):_*)))
    .source[String](TextLine(testCdxFile), sampleCdxLines)
    .sink[Tuple](CdxBackfillJob.getHBaseSink(testTable, testHost)) {
      outputBuffer =>

        it("should return a 1-element list (after join).") {
        // XXX:
          assert(outputBuffer.size === 1)
        }

        // Convert List[Tuple] to Map[Long, Long].
        val counts = outputBuffer.map(t => (t.getLong(0), t.getLong(1))).toMap
        it("should have the appropriate number of each status type") {
        // XXX:
          assert(counts(1) == 3)
        }
      }
    .run
    .finish
}
