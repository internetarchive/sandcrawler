package sandcrawler

import cascading.tuple.Fields
import cascading.tuple.Tuple
import com.twitter.scalding.JobTest
import com.twitter.scalding.Tsv
import com.twitter.scalding.TupleConversions
import com.twitter.scalding.TypedTsv
import org.apache.hadoop.hbase.io.ImmutableBytesWritable
import org.apache.hadoop.hbase.util.Bytes
import org.junit.runner.RunWith
import org.scalatest.FunSpec
import org.scalatest.junit.JUnitRunner
import org.slf4j.LoggerFactory
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import parallelai.spyglass.hbase.HBaseSource
import scala._

@RunWith(classOf[JUnitRunner])
class UnGrobidedDumpJobTest extends FunSpec with TupleConversions {

  val output = "/tmp/testOutput"
  val (testTable, testHost) = ("test-table", "dummy-host:2181")

  val log = LoggerFactory.getLogger(this.getClass.getName)

  val statusCode: Long = 200
  val statusBytes = Bytes.toBytes(statusCode)

  val sampleDataGrobid : List[List[Array[Byte]]] = List(
    ("sha1:SDKUVHC3YNNEGH5WAG5ZAAXWAEBNX4WT", statusBytes),
    ("sha1:35985C3YNNEGH5WAG5ZAAXWAEBNXJW56", statusBytes),
    ("sha1:885C3YNNEGH5WAG5ZAAXWA8BNXJWT6CZ", statusBytes),
    ("sha1:00904C3YNNEGH5WAG5ZA9XWAEBNXJWT6", statusBytes),
    ("sha1:249C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ", statusBytes),
    ("sha1:095893C3YNNEGH5WAG5ZAAXWAEBNXJWT", statusBytes))
      .map(pair => List(Bytes.toBytes(pair._1), pair._2))

  val sampleDataFile : List[List[Array[Byte]]] = List(
    ("sha1:K2DKSSVTXWPRMFDTWSTCQW3RVWRIOV3Q", """{c-json-data}""", "application/pdf", """{cdx-json-data}"""),
    ("sha1:C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ3WU", """{c-json-data}""", "application/pdf", """{cdx-json-data}"""),
    ("sha1:SDKUVHC3YNNEGH5WAG5ZAAXWAEBNX4WT", """{c-json-data}""", "application/pdf", """{cdx-json-data}"""),
    ("sha1:35985C3YNNEGH5WAG5ZAAXWAEBNXJW56", """{c-json-data}""", "application/pdf", """{cdx-json-data}"""),
    ("sha1:885C3YNNEGH5WAG5ZAAXWA8BNXJWT6CZ", """{c-json-data}""", "application/pdf", """{cdx-json-data}"""),
    ("sha1:00904C3YNNEGH5WAG5ZA9XWAEBNXJWT6", """{c-json-data}""", "application/pdf", """{cdx-json-data}"""),
    ("sha1:249C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ", """{c-json-data}""", "application/pdf", """{cdx-json-data}"""),
    ("sha1:095893C3YNNEGH5WAG5ZAAXWAEBNXJWT", """{c-json-data}""", "application/pdf", """{cdx-json-data}"""))
      .map(pair => List(Bytes.toBytes(pair._1),
                        Bytes.toBytes(pair._2),
                        Bytes.toBytes(pair._3),
                        Bytes.toBytes(pair._4)))

  JobTest("sandcrawler.UnGrobidedDumpJob")
    .arg("test", "")
    .arg("app.conf.path", "app.conf")
    .arg("output", output)
    .arg("hbase-table", testTable)
    .arg("zookeeper-hosts", testHost)
    .arg("debug", "true")
    .source[Tuple](UnGrobidedDumpJob.getHBaseColSource(testTable, testHost),
      sampleDataGrobid.map(l => new Tuple(l.map(s => {new ImmutableBytesWritable(s)}):_*)))
    .source[Tuple](UnGrobidedDumpJob.getHBaseKeySource(testTable, testHost),
      sampleDataFile.map(l => new Tuple(l.map(s => {new ImmutableBytesWritable(s)}):_*)))
    .sink[Tuple](TypedTsv[(String,String,String,String)](output)) {
      outputBuffer =>
      it("should return correct-length list.") {
        assert(outputBuffer.size === 2)
      }
    }
    .run
    .finish
}
