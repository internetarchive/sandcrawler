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

class FatcatScorableTest extends FlatSpec with Matchers {
  // scalastyle:off
  val FatcatString =
"""
{
  "abstracts": [],
  "refs": [],
  "contribs": [
    {
      "index": 0,
      "raw_name": "W Gaier",
      "surname": "Gaier",
      "role": "author",
      "extra": {
        "seq": "first"
      }
    }
  ],
  "publisher": "Elsevier BV",
  "pages": "186-187",
  "ext_ids": {
    "doi": "<<DOI>>"
  },
  "release_year": 1996,
  "release_stage": "published",
  "release_type": "article-journal",
  "container_id": "3nccslsn5jez3ixrp5skjyjxu4",
  "title": "<<TITLE>>",
  "state": "active",
  "ident": "pnri57u66ffytigdmyybbmouni",
  "work_id": "tdmqnfzm2nggrhfwzasyegvpyu",
  "revision": "e50bd04e-d0d4-4ee7-b7a4-6b4f079de154",
  "extra": {
    "crossref": {
      "alternative-id": [
        "0987-7983(96)87729-2"
      ],
      "type": "journal-article"
    }
  }
}
""".replace("<<DOI>>", "10.123/aBc")
  // scalastyle:on
  val FatcatStringWithGoodTitle = FatcatString.replace("<<TITLE>>", "Some Title")
  val FatcatStringWithMaximumTitle = FatcatString.replace("<<TITLE>>", "T" * Scorable.MaxTitleLength)
  val FatcatStringWithExcessiveTitle = FatcatString.replace("<<TITLE>>", "T" * Scorable.MaxTitleLength + "0")
  val FatcatStringWithNullTitle = FatcatString.replace("\"<<TITLE>>\"", "null")
  val FatcatStringWithEmptyTitle = FatcatString.replace("<<TITLE>>", "")
  val FatcatStringWithoutTitle = FatcatString.replace("title", "nottitle")
  val MalformedFatcatString = FatcatString.replace("}", "")
  val FatcatStringWithNoAuthors = FatcatString.replace("<<TITLE>>", "Some Valid Title").replace("contribs", "no-contribs")
  //val FatcatStringWrongType = FatcatString.replace("<<TITLE>>", "Some Valid Title").replace("journal-article", "other")
  //val FatcatStringNoType = FatcatString.replace("<<TITLE>>", "Some Valid Title").replace("type", "not-type")

  // Unit tests
  "FatcatScorable.jsonToMapFeatures()" should "handle invalid JSON" in {
    FatcatScorable.jsonToMapFeatures(MalformedFatcatString) should be (None)
  }

  it should "handle missing title" in {
    FatcatScorable.jsonToMapFeatures(FatcatStringWithoutTitle) should be (None)
  }

  it should "handle null title" in {
    FatcatScorable.jsonToMapFeatures(FatcatStringWithNullTitle) should be (None)
  }

  it should "handle empty title" in {
    FatcatScorable.jsonToMapFeatures(FatcatStringWithEmptyTitle) should be (None)
  }

  it should "handle subtitle" in {
    FatcatScorable.jsonToMapFeatures(
      """{"title": "short but not too short", "subtitle": "just right!", "ident": "pnri57u66ffytigdmyybbmouni", "work_id": "tdmqnfzm2nggrhfwzasyegvpyu", "DOI": "10.123/asdf", "type":"journal-article","contribs":[{ "raw_name" : "W Gaier", "surname" : "Gaier"}]}""") match {
      case None => fail()
      case Some(result) => result.slug shouldBe "shortbutnottooshortjustright"
    }
  }

  it should "handle empty subtitle" in {
    FatcatScorable.jsonToMapFeatures(
      """{"title": "short but not too short", "subtitle": "", "ident": "pnri57u66ffytigdmyybbmouni", "work_id": "tdmqnfzm2nggrhfwzasyegvpyu", "DOI": "10.123/asdf", "type":"journal-article", "contribs":[{ "raw_name" : "W Gaier", "surname" : "Gaier"}]}""") match {
      case None => fail()
      case Some(result) => result.slug shouldBe "shortbutnottooshort"
    }
  }

  it should "handle null subtitle" in {
    FatcatScorable.jsonToMapFeatures(
      """{"title": "short but not too short", "subtitle": null, "ident": "pnri57u66ffytigdmyybbmouni", "work_id": "tdmqnfzm2nggrhfwzasyegvpyu", "DOI": "10.123/asdf", "type":"journal-article", "contribs":[{ "raw_name" : "W Gaier", "surname" : "Gaier"}]}""") match {
      case None => fail()
      case Some(result) => result.slug shouldBe "shortbutnottooshort"
    }
  }

  it should "handle missing authors" in {
    // TODO: not actually removing these
    //FatcatScorable.jsonToMapFeatures(FatcatStringWithNoAuthors) should be (None)
    FatcatScorable.jsonToMapFeatures(FatcatStringWithNoAuthors)
  }

  it should "handle valid input" in {
    FatcatScorable.jsonToMapFeatures(FatcatStringWithGoodTitle) match {
      case None => fail()
      case Some(result) => {
        result.slug shouldBe "sometitle"
        Scorable.jsonToMap(result.json) match {
          case None => fail()
          case Some(map) => {
            map("title").asInstanceOf[String] shouldBe "Some Title"
            //map("doi").asInstanceOf[String] shouldBe "10.123/abc"
            map("fatcat_release").asInstanceOf[String] shouldBe "pnri57u66ffytigdmyybbmouni"
            map("fatcat_work").asInstanceOf[String] shouldBe "tdmqnfzm2nggrhfwzasyegvpyu"
            // TODO: full name? not just a string?
            map("authors").asInstanceOf[List[String]] shouldBe List("W Gaier")
            map("year").asInstanceOf[Double].toInt shouldBe 1996
          }
        }
      }
    }
  }

  "FatcatScorable.keepRecord()" should "return true for valid JSON with title" in {
    FatcatScorable.keepRecord(FatcatStringWithGoodTitle) shouldBe true
  }

  it should "return true for valid JSON with a title of maximum permitted length" in {
    FatcatScorable.keepRecord(FatcatStringWithMaximumTitle) shouldBe true
  }

  it should "return false for valid JSON with excessively long title" in {
    FatcatScorable.keepRecord(FatcatStringWithExcessiveTitle) shouldBe false
  }

  it should "return false for valid JSON with null title" in {
    FatcatScorable.keepRecord(FatcatStringWithNullTitle) shouldBe false
  }

  it should "return false for valid JSON with no title" in {
    FatcatScorable.keepRecord(FatcatStringWithoutTitle) shouldBe false
  }

  it should "return false for invalid JSON" in {
    FatcatScorable.keepRecord(FatcatStringWithoutTitle) shouldBe false
  }

}
