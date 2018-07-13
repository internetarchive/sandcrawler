package sandcrawler

import cascading.tuple.{Tuple, Fields}
import com.twitter.scalding.{JobTest, Tsv, TupleConversions}
import org.apache.hadoop.hbase.io.ImmutableBytesWritable
import org.apache.hadoop.hbase.util.Bytes
import org.junit.runner.RunWith
import org.scalatest.FunSpec
import org.scalatest.junit.JUnitRunner
import org.slf4j.LoggerFactory
import parallelai.spyglass.hbase.HBaseSource
import parallelai.spyglass.hbase.HBaseConstants.SourceMode
import scala._

@RunWith(classOf[JUnitRunner])
class HBaseMimeCountTest extends FunSpec with TupleConversions {

  val output = "/tmp/testOutput"
  val (testTable, testHost) = ("test-table", "dummy-host:2181")

  val log = LoggerFactory.getLogger(this.getClass.getName)

  val mimeType1 = "text/html"
  val mimeType2 = "application/pdf"

  val sampleData = List(
    List("sha1:K2DKSSVTXWPRMFDTWSTCQW3RVWRIOV3Q", mimeType1),
    List("sha1:C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ3WU", mimeType1),
    List("sha1:SDKUVHC3YNNEGH5WAG5ZAAXWAEBNX4WT", mimeType2),
    List("sha1:35985C3YNNEGH5WAG5ZAAXWAEBNXJW56", mimeType2),
    List("sha1:885C3YNNEGH5WAG5ZAAXWA8BNXJWT6CZ", mimeType2),
    List("sha1:00904C3YNNEGH5WAG5ZA9XWAEBNXJWT6", mimeType2),
    List("sha1:249C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ", mimeType1),
    List("sha1:095893C3YNNEGH5WAG5ZAAXWAEBNXJWT", mimeType2)
  )

  val mimeType1Count = sampleData.count(lst => lst(1) == mimeType1)
  val mimeType2Count = sampleData.count(lst => lst(1) == mimeType2)

  JobTest("sandcrawler.HBaseMimeCountJob")
    .arg("test", "")
    .arg("app.conf.path", "app.conf")
    .arg("output", output)
    .arg("hbase-table", testTable)
    .arg("zookeeper-hosts", testHost)
    .arg("debug", "true")
    .source[Tuple](HBaseCountJob.getHBaseSource(testTable, testHost, "file:mime"),
      sampleData.map(l => new Tuple(l.map(s => {new ImmutableBytesWritable(Bytes.toBytes(s))}):_*)))
      .sink[Tuple](Tsv(output)) {
        outputBuffer =>
        it("should return a 2-element list.") {
          assert(outputBuffer.size === 2)
        }

        // Convert List[Tuple] to Map[String, Integer].
        val counts = outputBuffer.map(t => (t.getString(0), t.getInteger(1))).toMap
        it("should have the appropriate number of each mime type") {
          assert(counts(mimeType1) == mimeType1Count)
          assert(counts(mimeType2) == mimeType2Count)
        }
    }
    .run
    .finish
}
