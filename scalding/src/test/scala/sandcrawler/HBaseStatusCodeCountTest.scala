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
class HBaseStatusCountTest extends FunSpec with TupleConversions {

  val output = "/tmp/testOutput"
  val (testTable, testHost) = ("test-table", "dummy-host:2181")

  val log = LoggerFactory.getLogger(this.getClass.getName)

  val statusType1 : Long = 200
  val statusType2 : Long = 404
  val statusType1Bytes = Bytes.toBytes(statusType1)
  val statusType2Bytes = Bytes.toBytes(statusType2)

  // TODO(bnewbold): now to express a null (empty value) in this list?
    val sampleData : List[List[Array[Byte]]] = List(
      ("sha1:K2DKSSVTXWPRMFDTWSTCQW3RVWRIOV3Q", statusType1Bytes),
      ("sha1:C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ3WU", statusType1Bytes),
      ("sha1:SDKUVHC3YNNEGH5WAG5ZAAXWAEBNX4WT", statusType2Bytes),
      ("sha1:35985C3YNNEGH5WAG5ZAAXWAEBNXJW56", statusType2Bytes),
      ("sha1:885C3YNNEGH5WAG5ZAAXWA8BNXJWT6CZ", statusType2Bytes),
      ("sha1:00904C3YNNEGH5WAG5ZA9XWAEBNXJWT6", statusType2Bytes),
      ("sha1:249C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ", statusType1Bytes),
      ("sha1:095893C3YNNEGH5WAG5ZAAXWAEBNXJWT", statusType2Bytes))
        .map(pair => List(Bytes.toBytes(pair._1), pair._2))

  val statusType1Count = sampleData.count(lst => lst(1) == statusType1Bytes)
  val statusType2Count = sampleData.count(lst => lst(1) == statusType2Bytes)

  JobTest("sandcrawler.HBaseStatusCountJob")
    .arg("test", "")
    .arg("app.conf.path", "app.conf")
    .arg("output", output)
    .arg("hbase-table", testTable)
    .arg("zookeeper-hosts", testHost)
    .arg("debug", "true")
    .source[Tuple](HBaseCountJob.getHBaseSource(testTable, testHost, "grobid0:status_code"),
      sampleData.map(l => new Tuple(l.map(s => {new ImmutableBytesWritable(s)}):_*)))
    .sink[Tuple](TypedTsv[(Long, Long)](output)) {
      outputBuffer =>
      it("should return a 2-element list.") {
        assert(outputBuffer.size === 2)
      }

      // Convert List[Tuple] to Map[Long, Long].
      val counts = outputBuffer.map(t => (t.getLong(0), t.getLong(1))).toMap
      it("should have the appropriate number of each status type") {
        assert(counts(statusType1) == statusType1Count)
        assert(counts(statusType2) == statusType2Count)
      }
    }
    .run
    .finish
}
