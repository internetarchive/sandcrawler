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
class HBaseStatusCountTest extends FunSpec with TupleConversions {

  val output = "/tmp/testOutput"
  val (testTable, testHost) = ("test-table", "dummy-host:2181")

  val log = LoggerFactory.getLogger(this.getClass.getName)

  val statusType1 = "200"
  val statusType2 = "404"

  val sampleData = List(
    List("sha1:K2DKSSVTXWPRMFDTWSTCQW3RVWRIOV3Q", statusType1),
    List("sha1:C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ3WU", statusType1),
    List("sha1:SDKUVHC3YNNEGH5WAG5ZAAXWAEBNX4WT", statusType2),
    List("sha1:35985C3YNNEGH5WAG5ZAAXWAEBNXJW56", statusType2),
    List("sha1:885C3YNNEGH5WAG5ZAAXWA8BNXJWT6CZ", statusType2),
    List("sha1:00904C3YNNEGH5WAG5ZA9XWAEBNXJWT6", statusType2),
    List("sha1:249C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ", statusType1),
    List("sha1:095893C3YNNEGH5WAG5ZAAXWAEBNXJWT", statusType2)
  )

  val statusType1Count = sampleData.count(lst => lst(1) == statusType1)
  val statusType2Count = sampleData.count(lst => lst(1) == statusType2)

  JobTest("sandcrawler.HBaseStatusCountJob")
    .arg("test", "")
    .arg("app.conf.path", "app.conf")
    .arg("output", output)
    .arg("hbase-table", testTable)
    .arg("zookeeper-hosts", testHost)
    .arg("debug", "true")
    .source[Tuple](HBaseCountJob.getHBaseSource(testTable, testHost, "grobid0:status"),
      sampleData.map(l => new Tuple(l.map(s => {new ImmutableBytesWritable(Bytes.toBytes(s))}):_*)))
      .sink[Tuple](Tsv(output)) {
        outputBuffer =>
        it("should return a 2-element list.") {
          assert(outputBuffer.size === 2)
        }

        // Convert List[Tuple] to Map[String, Integer].
        val counts = outputBuffer.map(t => (t.getString(0), t.getInteger(1))).toMap
        it("should have the appropriate number of each status type") {
          assert(counts(statusType1) == statusType1Count)
          assert(counts(statusType2) == statusType2Count)
        }
    }
    .run
    .finish
}
