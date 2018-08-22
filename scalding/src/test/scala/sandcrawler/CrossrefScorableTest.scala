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

class CrossrefScorableTest extends FlatSpec with Matchers {
  // scalastyle:off
  val CrossrefString =
"""
{ "_id" : { "$oid" : "5a553d5988a035a45bf50ed3" },
  "indexed" : { "date-parts" : [ [ 2017, 10, 23 ] ],
    "date-time" : "2017-10-23T17:19:16Z",
    "timestamp" : { "$numberLong" : "1508779156477" } },
  "reference-count" : 0,
  "publisher" : "Elsevier BV",
  "issue" : "3",
  "license" : [ { "URL" : "http://www.elsevier.com/tdm/userlicense/1.0/",
                    "start" : { "date-parts" : [ [ 1996, 1, 1 ] ],
                                "date-time" : "1996-01-01T00:00:00Z",
                                "timestamp" : { "$numberLong" : "820454400000" } },
                                "delay-in-days" : 0, "content-version" : "tdm" }],
  "content-domain" : { "domain" : [], "crossmark-restriction" : false },
  "published-print" : { "date-parts" : [ [ 1996 ] ] },
  "DOI" : "<<DOI>>",
  "type" : "journal-article",
  "created" : { "date-parts" : [ [ 2002, 7, 25 ] ],
    "date-time" : "2002-07-25T15:09:41Z",
    "timestamp" : { "$numberLong" : "1027609781000" } },
  "page" : "186-187",
  "source" : "Crossref",
  "is-referenced-by-count" : 0,
  "title" : [ "<<TITLE>>" ],
  "prefix" : "10.1016",
  "volume" : "9",
  "author" : [ { "given" : "W", "family" : "Gaier", "affiliation" : [] } ],
  "member" : "78",
  "container-title" : [ "Journal de PÃ©diatrie et de PuÃ©riculture" ],
  "link" : [ { "URL" :  "http://api.elsevier.com/content/article/PII:0987-7983(96)87729-2?httpAccept=text/xml",
               "content-type" : "text/xml",
                 "content-version" : "vor",
                 "intended-application" : "text-mining" },
               { "URL" :
  "http://api.elsevier.com/content/article/PII:0987-7983(96)87729-2?httpAccept=text/plain",
                 "content-type" : "text/plain",
                 "content-version" : "vor",
                 "intended-application" : "text-mining" } ],
  "deposited" : { "date-parts" : [ [ 2015, 9, 3 ] ],
                  "date-time" : "2015-09-03T10:03:43Z",
                  "timestamp" : { "$numberLong" : "1441274623000" } },
  "score" : 1,
  "issued" : { "date-parts" : [ [ 1996 ] ] },
  "references-count" : 0,
  "alternative-id" : [ "0987-7983(96)87729-2" ],
  "URL" : "http://dx.doi.org/10.1016/0987-7983(96)87729-2",
  "ISSN" : [ "0987-7983" ],
  "issn-type" : [ { "value" : "0987-7983", "type" : "print" } ],
  "subject" : [ "Pediatrics, Perinatology, and Child Health" ]
}
"""
  // scalastyle:on
  val CrossrefStringWithGoodTitle = CrossrefString.replace("<<TITLE>>", "Some Title")
  val CrossrefStringWithMaximumTitle = CrossrefString.replace("<<TITLE>>", "T" * Scorable.MaxTitleLength)
  val CrossrefStringWithExcessiveTitle = CrossrefString.replace("<<TITLE>>", "T" * Scorable.MaxTitleLength + "0")
  val CrossrefStringWithNullTitle = CrossrefString.replace("\"<<TITLE>>\"", "null")
  val CrossrefStringWithEmptyTitle = CrossrefString.replace("<<TITLE>>", "")
  val CrossrefStringWithoutTitle = CrossrefString.replace("title", "nottitle")
  val MalformedCrossrefString = CrossrefString.replace("}", "")

  // Unit tests
  "CrossrefScorable.jsonToMapFeatures()" should "handle invalid JSON" in {
    val result = CrossrefScorable.jsonToMapFeatures(MalformedCrossrefString)
    result.slug shouldBe Scorable.NoSlug
  }

  it should "handle missing title" in {
    val result = CrossrefScorable.jsonToMapFeatures(CrossrefStringWithoutTitle)
    result.slug shouldBe Scorable.NoSlug
  }

  it should "handle null title" in {
    val result = CrossrefScorable.jsonToMapFeatures(CrossrefStringWithNullTitle)
    result.slug shouldBe Scorable.NoSlug
  }

  it should "handle empty title" in {
    val result = CrossrefScorable.jsonToMapFeatures(CrossrefStringWithEmptyTitle)
    result.slug shouldBe Scorable.NoSlug
  }

  it should "handle valid input" in {
    val result = CrossrefScorable.jsonToMapFeatures(CrossrefStringWithGoodTitle)
    result.slug shouldBe "sometitle"
    Scorable.jsonToMap(result.json) match {
      case None => fail()
      case Some(map) => {
        map("title").asInstanceOf[String] shouldBe "Some Title"
      }
    }
  }

  "CrossrefScorable.keepRecord()" should "return true for valid JSON with title" in {
    CrossrefScorable.keepRecord(CrossrefStringWithGoodTitle) shouldBe true
  }

  it should "return true for valid JSON with a title of maximum permitted length" in {
    CrossrefScorable.keepRecord(CrossrefStringWithMaximumTitle) shouldBe true
  }

  it should "return false for valid JSON with excessively long title" in {
    CrossrefScorable.keepRecord(CrossrefStringWithExcessiveTitle) shouldBe false
  }

  it should "return false for valid JSON with null title" in {
    CrossrefScorable.keepRecord(CrossrefStringWithNullTitle) shouldBe false
  }

  it should "return false for valid JSON with no title" in {
    CrossrefScorable.keepRecord(CrossrefStringWithoutTitle) shouldBe false
  }

  it should "return false for invalid JSON" in {
    CrossrefScorable.keepRecord(CrossrefStringWithoutTitle) shouldBe false
  }
}
