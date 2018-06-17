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

/**
 * Example of how to define tests for HBaseSource
 */
@RunWith(classOf[JUnitRunner])
class HBaseRowCountTest extends FunSpec with TupleConversions {

  val output = "/tmp/testOutput"
  val (test_table, test_host) = ("test-table", "dummy-host:2181")

  val log = LoggerFactory.getLogger(this.getClass.getName)

  val sampleData = List(
    List("sha1:K2DKSSVTXWPRMFDTWSTCQW3RVWRIOV3Q", "a", "b"),
    List("sha1:C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ3WU", "a", "b"),
    List("sha1:SDKUVHC3YNNEGH5WAG5ZAAXWAEBNX4WT", "a", "b"),
    List("sha1:35985C3YNNEGH5WAG5ZAAXWAEBNXJW56", "a", "b"),
    List("sha1:885C3YNNEGH5WAG5ZAAXWA8BNXJWT6CZ", "a", "b"),
    List("sha1:00904C3YNNEGH5WAG5ZA9XWAEBNXJWT6", "a", "b"),
    List("sha1:249C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ", "a", "b"),
    List("sha1:095893C3YNNEGH5WAG5ZAAXWAEBNXJWT", "a", "b")
  )

  JobTest("sandcrawler.HBaseRowCountJob")
    .arg("test", "")
    .arg("app.conf.path", "app.conf")
    .arg("output", output)
    .arg("hbase-table", test_table)
    .arg("zookeeper-hosts", test_host)
    .arg("debug", "true")
    .source[Tuple](HBaseRowCountJob.getHBaseSource(test_table, test_host),
      sampleData.map(l => new Tuple(l.map(s => {new ImmutableBytesWritable(Bytes.toBytes(s))}):_*)))
      .sink[Tuple](Tsv(output)) {
      outputBuffer =>

        it("should return the test data provided.") {
          println("outputBuffer.size => " + outputBuffer.size)
          assert(outputBuffer.size === 1)
        }

        it("should return the correct count") {
          println("raw output => " + outputBuffer)
          assert(outputBuffer(0).getObject(0) === 8)
        }
    }
    .run
    .finish

}
