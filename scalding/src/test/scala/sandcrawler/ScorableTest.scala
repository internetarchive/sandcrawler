package sandcrawler

import cascading.tuple.Fields
import cascading.tuple.Tuple
import com.twitter.scalding.{JobTest, TextLine, TypedTsv, TupleConversions}
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

  "titleToSlug()" should "extract the parts of titles before a colon" in {
    Scorable.titleToSlug("HELLO:there") shouldBe "hello"
  }

  it should "extract an entire colon-less string" in {
    Scorable.titleToSlug("hello THERE") shouldBe "hello there"
  }

  it should "return Scorable.NoSlug if given empty string" in {
    Scorable.titleToSlug("") shouldBe Scorable.NoSlug
  }

  it should "return Scorable.NoSlug if given null" in {
    Scorable.titleToSlug(null) shouldBe Scorable.NoSlug
  }

  "titleToSlug()" should "strip punctuation" in {
    Scorable.titleToSlug("HELLO!:the:re") shouldBe "hello"
    Scorable.titleToSlug("a:b:c") shouldBe "a"
    Scorable.titleToSlug(
      "If you're happy and you know it, clap your hands!") shouldBe "if youre happy and you know it clap your hands"
  }

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
}
