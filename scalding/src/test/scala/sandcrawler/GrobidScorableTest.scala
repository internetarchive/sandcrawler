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

class GrobidScorableTest extends FlatSpec with Matchers {
  val GrobidString = """
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
  val GrobidStringWithGoodTitle = GrobidString.replace("<<TITLE>>", "Dummy Example File")
  val GrobidStringWithMaximumTitle = GrobidString.replace("<<TITLE>>", "T" * Scorable.MaxTitleLength)
  val GrobidStringWithExcessiveTitle = GrobidString.replace("<<TITLE>>", "T" * Scorable.MaxTitleLength + "0")
  val GrobidStringWithNullTitle = GrobidString.replace("\"<<TITLE>>\"", "null")
  val GrobidStringWithoutTitle = GrobidString.replace("title", "nottitle")
  val MalformedGrobidString = GrobidString.replace("}", "")
  val Key = "Dummy Key"

  // Unit tests

  "GrobidScorable.jsonToMapFeatures()" should "handle invalid JSON" in {
    GrobidScorable.jsonToMapFeatures(Key, MalformedGrobidString) should be (None)
  }

  it should "handle null title" in {
    GrobidScorable.jsonToMapFeatures(Key, GrobidStringWithNullTitle) should be (None)
  }

  it should "handle missing title" in {
    GrobidScorable.jsonToMapFeatures(Key, GrobidStringWithoutTitle) should be (None)
  }

  it should "handle valid input" in {
    GrobidScorable.jsonToMapFeatures(Key, GrobidStringWithGoodTitle) match {
      case None => fail()
      case Some(result) => {
        result.slug shouldBe "dummyexamplefile"
        Scorable.jsonToMap(result.json) match {
          case None => fail()
          case Some(map) => {
            map should contain key "title"
            map("title").asInstanceOf[String] shouldBe "Dummy Example File"
            map("authors").asInstanceOf[List[String]] shouldBe List("Brewster Kahle", "J Doe")
          }
        }
      }
    }
  }

  "GrobidScorable.keepRecord()" should "return true for valid JSON with title" in {
    GrobidScorable.keepRecord(GrobidStringWithGoodTitle) shouldBe true
  }

  it should "return true for valid JSON with a title of maximum permitted length" in {
    GrobidScorable.keepRecord(GrobidStringWithMaximumTitle) shouldBe true
  }

  it should "return false for valid JSON with excessively long title" in {
    GrobidScorable.keepRecord(GrobidStringWithExcessiveTitle) shouldBe false
  }

  it should "return false for valid JSON with null title" in {
    GrobidScorable.keepRecord(GrobidStringWithNullTitle) shouldBe false
  }

  it should "return false for valid JSON with no title" in {
    GrobidScorable.keepRecord(GrobidStringWithoutTitle) shouldBe false
  }

  it should "return false for invalid JSON" in {
    GrobidScorable.keepRecord(GrobidStringWithoutTitle) shouldBe false
  }
}
