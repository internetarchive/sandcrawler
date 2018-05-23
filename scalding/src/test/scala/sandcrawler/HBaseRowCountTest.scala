package example

import org.junit.runner.RunWith
import com.twitter.scalding.{JobTest, TupleConversions}
import org.scalatest.FunSpec
import org.scalatest.junit.JUnitRunner
import org.slf4j.LoggerFactory
import org.apache.hadoop.hbase.io.ImmutableBytesWritable
import cascading.tuple.{Tuple, Fields}
import org.apache.hadoop.hbase.util.Bytes
import scala._
import com.twitter.scalding.Tsv
import parallelai.spyglass.hbase.HBaseSource
import parallelai.spyglass.hbase.HBaseConstants.SourceMode

/**
 * Example of how to define tests for HBaseSource
 */
@RunWith(classOf[JUnitRunner])
class HBaseRowCountTest extends FunSpec with TupleConversions {

  val output = "/tmp/testOutput"

  val log = LoggerFactory.getLogger(this.getClass.getName)

  val sampleData = List(
    List("sha1:K2DKSSVTXWPRMFDTWSTCQW3RVWRIOV3Q", "a", "b"),
    List("sha1:C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ3WU", "a", "b")
  )

  JobTest("sandcrawler.HBaseRowCountJob")
    .arg("test", "")
    .arg("app.conf.path", "app.conf")
    .arg("output", output)
    .arg("debug", "true")
    .source[Tuple](
    new HBaseSource(
      //"table_name",
      //"quorum_name:2181",
      "wbgrp-journal-extract-0-qa",
      "mtrcs-zk1.us.archive.org:2181",
      new Fields("key"),
      List("file"),
      List(new Fields("size", "mimetype")),
      sourceMode = SourceMode.GET_LIST, keyList = List("sha1:K2DKSSVTXWPRMFDTWSTCQW3RVWRIOV3Q", "sha1:C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ3WU")),
      sampleData.map(l => new Tuple(l.map(s => {new ImmutableBytesWritable(Bytes.toBytes(s))}):_*)))
    .sink[Tuple](Tsv(output format "get_list")) {
      outputBuffer =>
        log.debug("Output => " + outputBuffer)

        it("should return the test data provided.") {
          println("outputBuffer.size => " + outputBuffer.size)
          assert(outputBuffer.size === 2)
        }
    }
    .run
    .finish

}
