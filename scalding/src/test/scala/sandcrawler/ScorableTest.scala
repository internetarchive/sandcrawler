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

class ScorableTest extends FlatSpec with Matchers {
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
  "jsonToMap()" should "return a map, given a legal JSON string" in {
    Scorable.jsonToMap(JsonString) should not be (None)
  }

  it should "return None, given illegal JSON" in {
    Scorable.jsonToMap("illegal{,json{{") should be (None)
  }

  "computeOutput()" should "return Scorable.MaxScore if given identical ReduceFeatures" in {
    val score = Scorable.computeSimilarity(
      new ReduceFeatures(JsonString), new ReduceFeatures(JsonString))
    score shouldBe Scorable.MaxScore
  }

  "computeOutput()" should "be case-insensitive" in {
    val left = JsonString.replace("<<TITLE>>", "A TITLE UPPER CASE")
    val right = JsonString.replace("<<TITLE>>", "a title upper case")
    val score = Scorable.computeSimilarity(
      new ReduceFeatures(left), new ReduceFeatures(right))
    score shouldBe Scorable.MaxScore
  }
}
