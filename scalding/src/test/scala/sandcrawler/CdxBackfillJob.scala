
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
import scala.util.parsing.json.JSON

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
      """edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz""")))
    // redirect
    assert(false === keepCdx(lineToCdxLine(
      "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 301 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz")))
    // not PDF
    assert(false === keepCdx(lineToCdxLine(
      """edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf text/plain 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz""")))
    // invalid base32 SHA1
    assert(false === keepCdx(lineToCdxLine(
      """edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FE010101010101010101VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz""")))
    assert(false === keepCdx(lineToCdxLine(
      """edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL33FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz""")))
    // dashed field
    assert(false === keepCdx(lineToCdxLine(
      """edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 - application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz""")))
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
    // this particular test copied from python test_backfill_hbase_from_cdx.py
    val row = cdxLineToRow(lineToCdxLine(
      "eu,eui,cadmus)/bitstream/handle/1814/36635/rscas_2015_03.pdf;jsessionid=761393014319a39f40d32ae3eb3a853f?sequence=1 20170705062202 http://cadmus.eui.eu/bitstream/handle/1814/36635/RSCAS_2015_03.pdf%3Bjsessionid%3D761393014319A39F40D32AE3EB3A853F?sequence%3D1 application/PDF 200 MPCXVWMUTRUGFP36SLPHKDLY6NGU4S3J - - 854156 328850624 CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz"))

    assert(row._1 == "sha1:MPCXVWMUTRUGFP36SLPHKDLY6NGU4S3J")
    JSON.parseFull(row._2) match {
      case Some(obj: Map[String, Any]) => {
        assert(obj("u") == "http://cadmus.eui.eu/bitstream/handle/1814/36635/RSCAS_2015_03.pdf%3Bjsessionid%3D761393014319A39F40D32AE3EB3A853F?sequence%3D1")
        assert(obj("f") == "CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz")
        assert(obj("c") == 854156)
        assert(obj("o") == 328850624)
        assert(obj("d") == "2017-07-05T06:22:02Z")
      }
      case other => assert(false)
    }
    JSON.parseFull(row._3) match {
      case Some(obj: Map[String, Any]) => {
        assert(obj("surt") == "eu,eui,cadmus)/bitstream/handle/1814/36635/rscas_2015_03.pdf;jsessionid=761393014319a39f40d32ae3eb3a853f?sequence=1")
        assert(obj("dt") == "20170705062202")
        assert(obj("url") == "http://cadmus.eui.eu/bitstream/handle/1814/36635/RSCAS_2015_03.pdf%3Bjsessionid%3D761393014319A39F40D32AE3EB3A853F?sequence%3D1")
        assert(obj("c_size") == 854156)
        assert(obj("offset") == 328850624)
        assert(obj("warc") == "CITESEERX-CRAWL-2017-06-20-20170705061647307-00039-00048-wbgrp-svc284/CITESEERX-CRAWL-2017-06-20-20170705062052659-00043-31209~wbgrp-svc284.us.archive.org~8443.warc.gz")
      }
      case other => assert(false)
    }
    assert(row._4 == "application/pdf")
  }

}

@RunWith(classOf[JUnitRunner])
class CdxBackfillJobTest extends FunSpec with TupleConversions {

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
    "0" -> """edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz""",
    // has existing SHA1
    "1" -> """edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ3WU - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz""",
    // HTTP status code
    "2" -> """edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 301 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz""",
    // not CDX (prefixed with hash)
    "3" -> """#edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/pdf 200 WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz""",
    // not PDF
    "4" -> """edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf 20170828233154 https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf application/film 200 AAAAAEA62TEU4F52Y5DOVQ62VET4QJW7G - - 210251 931661233 SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz"""
  )

  JobTest("sandcrawler.CdxBackfillJob")
    .arg("test", "")
    .arg("app.conf.path", "app.conf")
    .arg("hbase-table", testTable)
    .arg("zookeeper-hosts", testHost)
    .arg("cdx-input-path", testCdxFile)
    .arg("debug", "true")
    .source[Tuple](CdxBackfillJob.getHBaseSource(testTable, testHost),
      sampleData.map(l => new Tuple(l.map(s => {new ImmutableBytesWritable(s)}):_*)))
    .source(TextLine(testCdxFile), sampleCdxLines)
    .sink[(ImmutableBytesWritable, ImmutableBytesWritable, ImmutableBytesWritable, ImmutableBytesWritable)](CdxBackfillJob.getHBaseSink(testTable, testHost)) {
      outputBuffer =>

        val buf0 = outputBuffer(0)
        val row0 = List(buf0._1, buf0._2, buf0._3, buf0._4).map(b => Bytes.toString(b.copyBytes()))

        it("should return a 1-element list (after join).") {
          assert(outputBuffer.size === 1)
        }

        it("should insert the valid, new CDX line") {
          assert(row0(0) == "sha1:WL3FEA62TEU4F52Y5DOVQ62VET4QJW7G")
          JSON.parseFull(row0(1)) match {
            case Some(obj: Map[String, Any]) => {
              assert(obj("u") == "https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf")
              assert(obj("f") == "SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz")
              assert(obj("c") == 210251)
              assert(obj("o") == 931661233)
              assert(obj("d") == "2017-08-28T23:31:54Z")
            }
            case other => assert(false)
          }
          JSON.parseFull(row0(2)) match {
            case Some(obj: Map[String, Any]) => {
              assert(obj("surt") == "edu,upenn,ldc)/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf")
              assert(obj("dt") == "20170828233154")
              assert(obj("url") == "https://www.ldc.upenn.edu/sites/www.ldc.upenn.edu/files/medar2009-large-arabic-broadcast-collection.pdf")
              assert(obj("c_size") == 210251)
              assert(obj("offset") == 931661233)
              assert(obj("warc") == "SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828231135742-00000-00009-wbgrp-svc284/SEMSCHOLAR-PDF-CRAWL-2017-08-04-20170828232253025-00005-3480~wbgrp-svc284.us.archive.org~8443.warc.gz")
            }
            case other => assert(false)
          }
          assert(row0(3) == "application/pdf")
        }
      }
    .run
    .finish
}
