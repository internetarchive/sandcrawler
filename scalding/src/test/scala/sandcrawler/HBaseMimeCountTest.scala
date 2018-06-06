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
class HBaseMimeCountTest extends FunSpec with TupleConversions {

  val output = "/tmp/testOutput"

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

  val mimeType1Count = 3
  val mimeType2Count = 5

  JobTest("sandcrawler.HBaseMimeCountJob")
    .arg("test", "")
    .arg("app.conf.path", "app.conf")
    .arg("output", output)
    .arg("debug", "true")
    .source[Tuple](HBaseMimeCountJob.getHBaseSource,
      sampleData.map(l => new Tuple(l.map(s => {new ImmutableBytesWritable(Bytes.toBytes(s))}):_*)))
      .sink[Tuple](Tsv(output)) {
        outputBuffer =>
        it("should return a 2-element list.") {
          println("outputBuffer.size => " + outputBuffer.size)
          println("outputBuffer(0) => " + outputBuffer(0))
          println("outputBuffer(1) => " + outputBuffer(1))
          assert(outputBuffer.size === 2)
        }

        val counts = outputBuffer.map(t => (t.getString(0), t.getInteger(1))).toMap

        it("should have the appropriate number of each mime type") {
          assert(counts(mimeType1) == mimeType1Count)
          assert(counts(mimeType2) == mimeType2Count)
        }
    }
    .run
    .finish

}
