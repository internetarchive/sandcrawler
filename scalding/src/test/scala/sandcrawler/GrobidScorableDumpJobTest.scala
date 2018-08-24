
package sandcrawler

import cascading.tuple.Fields
import cascading.tuple.Tuple
import com.twitter.scalding.JobTest
import com.twitter.scalding.TextLine
import com.twitter.scalding.TupleConversions
import com.twitter.scalding.TypedTsv
import org.apache.hadoop.hbase.io.ImmutableBytesWritable
import org.apache.hadoop.hbase.util.Bytes
import org.scalatest._
import parallelai.spyglass.hbase.HBaseConstants.SourceMode

class GrobidScorableDumpJobTest extends FlatSpec with Matchers {
  //scalastyle:off
  val JsonString = """
{
  "title": "<<TITLE>>",
  "authors": [
    {"name": "Brewster Kahle"},
    {"name": "J Doe"}
  ],
  "journal": {
    "name": "Dummy Example File. Journal of Fake News. pp. 1-2. ISSN 1234-5678",
    "eissn": null,
    "issn": null,
    "issue": null,
    "publisher": null,
    "volume": null
  },
  "date": "2000",
  "doi": null,
  "citations": [
    { "authors": [{"name": "A Seaperson"}],
      "date": "2001",
      "id": "b0",
      "index": 0,
      "issue": null,
      "journal": "Letters in the Alphabet",
      "publisher": null,
      "title": "Everything is Wonderful",
      "url": null,
      "volume": "20"},
    { "authors": [],
      "date": "2011-03-28",
      "id": "b1",
      "index": 1,
      "issue": null,
      "journal": "The Dictionary",
      "publisher": null,
      "title": "All about Facts",
      "url": null,
      "volume": "14"}
  ],
  "abstract": "Everything you ever wanted to know about nothing",
  "body": "Introduction \nEverything starts somewhere, as somebody [1]  once said. \n\n In Depth \n Meat \nYou know, for kids. \n Potatos \nQED.",
  "acknowledgement": null,
  "annex": null
}
"""
  // scalastyle:on
  val JsonStringWithTitle = JsonString.replace("<<TITLE>>", "Dummy Example File")
  val JsonStringWithoutTitle = JsonString.replace("title", "nottitle")
  val MalformedJsonString = JsonString.replace("}", "")

  //  Pipeline tests
  val output = "/tmp/testOutput"
  val input = "/tmp/testInput"
  val (testTable, testHost) = ("test-table", "dummy-host:2181")

  val Sha1Strings : List[String] = List(
    "sha1:K2DKSSVTXWPRMFDTWSTCQW3RVWRIOV3Q",  // good
    "sha1:C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ3WU",  // good
    "sha1:SDKUVHC3YNNEGH5WAG5ZAAXWAEBNX4WT",  // good
    "sha1:35985C3YNNEGH5WAG5ZAAXWAEBNXJW56",  // bad status
    "sha1:93187A85273589347598473894839443",  // malformed
    "sha1:024937534094897039547e9824382943")  // bad status

  val JsonStrings : List[String] = List(
    JsonString.replace("<<TITLE>>", "Title 1: The Classic"),
    JsonString.replace("<<TITLE>>", "Title 2: TNG"),
    JsonString.replace("<<TITLE>>", "Title 3: The Sequel"),
    // This will have bad status.
    JsonString.replace("<<TITLE>>", "Title 1: The Classic"),
    MalformedJsonString,
    // This will have bad status.
    JsonString.replace("<<TITLE>>", "Title 2: Not TNG")
  )

  // bnewbold: status codes aren't strings, they are uint64
  val Ok : Long = 200
  val Bad : Long = 400
  val StatusCodes = List(Ok, Ok, Ok, Bad, Ok, Bad)

  val SampleDataHead : List[Tuple] = (Sha1Strings, JsonStrings, StatusCodes)
    .zipped
    .toList
    .map { case (sha, json, status) => List(Bytes.toBytes(sha), Bytes.toBytes(json), Bytes.toBytes(status)) }
    .map { l => new Tuple(l.map(s => {new ImmutableBytesWritable(s)}):_*) }

  // scalastyle:off null
  // Add example of lines without GROBID data
  val SampleData = SampleDataHead :+ new Tuple(
    new ImmutableBytesWritable(Bytes.toBytes("sha1:35985C3YNNEGH5WAG5ZAA88888888888")), null, null)
  // scalastyle:on null

  JobTest("sandcrawler.GrobidScorableDumpJob")
    .arg("test", "")
    .arg("app.conf.path", "app.conf")
    .arg("output", output)
    .arg("hbase-table", testTable)
    .arg("zookeeper-hosts", testHost)
    .arg("debug", "true")
    .source[Tuple](GrobidScorable.getHBaseSource(testTable, testHost), SampleData)
    .sink[(String, String)](TypedTsv[(String, String)](output)) {
      outputBuffer =>
      "The pipeline" should "return correct-length list" in {
        outputBuffer should have length 3
      }
    }
    .run
    .finish
}
