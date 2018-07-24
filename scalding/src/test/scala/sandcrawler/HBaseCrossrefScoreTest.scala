package sandcrawler

import cascading.tuple.Fields
import org.scalatest._
import parallelai.spyglass.hbase.HBaseConstants.SourceMode

class HBaseCrossrefScoreTest extends FlatSpec with Matchers {
  val GrobidString = """
{
  "title": "Dummy Example File",
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
  val GrobidStringWithoutTitle = GrobidString.replace("title", "nottitle")
  val MalformedGrobidString = GrobidString.replace("}", "")

  "titleToSlug()" should "extract the parts of titles before a colon" in {
    val slug = HBaseCrossrefScore.titleToSlug("hello:there")
    slug shouldBe "hello"
  }
  it should "extract an entire colon-less string" in {
    val slug = HBaseCrossrefScore.titleToSlug("hello there")
    slug shouldBe "hello there"
  }

  "grobidToSlug()" should "get the right slug for a grobid json string" in {
    val slug = HBaseCrossrefScore.grobidToSlug(GrobidString)
    slug should contain ("Dummy Example File")
  }

  "grobidToSlug()" should "return None if given json string without title" in {
    val slug = HBaseCrossrefScore.grobidToSlug(GrobidStringWithoutTitle)
    slug shouldBe None
  }

  "grobidToSlug()" should "return None if given a malformed json string" in {
    val slug = HBaseCrossrefScore.grobidToSlug(MalformedGrobidString)
    slug shouldBe None
  }
}
