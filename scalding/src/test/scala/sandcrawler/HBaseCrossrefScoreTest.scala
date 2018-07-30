package sandcrawler

import cascading.tuple.Fields
import cascading.tuple.Tuple
import com.twitter.scalding.{JobTest, TextLine, TypedTsv, TupleConversions}
import org.apache.hadoop.hbase.io.ImmutableBytesWritable
import org.apache.hadoop.hbase.util.Bytes
import org.scalatest._
import parallelai.spyglass.hbase.HBaseConstants.SourceMode

class HBaseCrossrefScoreTest extends FlatSpec with Matchers {
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
  val GrobidStringWithTitle = GrobidString.replace("<<TITLE>>", "Dummy Example File")
  val GrobidStringWithoutTitle = GrobidString.replace("title", "nottitle")
  val MalformedGrobidString = GrobidString.replace("}", "")

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
  val CrossrefStringWithTitle = CrossrefString.replace("<<TITLE>>", "SomeTitle")
  val CrossrefStringWithoutTitle = CrossrefString.replace("title", "nottitle")
  val MalformedCrossrefString = CrossrefString.replace("}", "")

  // Unit tests

  "titleToSlug()" should "extract the parts of titles before a colon" in {
    val slug = HBaseCrossrefScore.titleToSlug("HELLO:there")
    slug should contain ("hello")
  }

  it should "extract an entire colon-less string" in {
    val slug = HBaseCrossrefScore.titleToSlug("hello THERE")
    slug should contain ("hello there")
  }

  it should "return None if given empty string" in {
    HBaseCrossrefScore.titleToSlug("") shouldBe None
  }

  "grobidToSlug()" should "get the right slug for a grobid json string" in {
    val slug = HBaseCrossrefScore.grobidToSlug(GrobidStringWithTitle)
    slug should contain ("dummy example file")
  }

  it should "return None if given json string without title" in {
    val slug = HBaseCrossrefScore.grobidToSlug(GrobidStringWithoutTitle)
    slug shouldBe None
  }

  it should "return None if given a malformed json string" in {
    val slug = HBaseCrossrefScore.grobidToSlug(MalformedGrobidString)
    slug shouldBe None
  }

  it should "return None if given an empty json string" in {
    val slug = HBaseCrossrefScore.grobidToSlug("")
    slug shouldBe None
  }

  "crossrefToSlug()" should "get the right slug for a crossref json string" in {
    val slug = HBaseCrossrefScore.crossrefToSlug(CrossrefStringWithTitle)
    slug should contain ("sometitle")
  }

  it should "return None if given json string without title" in {
    val slug = HBaseCrossrefScore.grobidToSlug(CrossrefStringWithoutTitle)
    slug shouldBe None
  }

  it should "return None if given a malformed json string" in {
    val slug = HBaseCrossrefScore.grobidToSlug(MalformedCrossrefString)
    slug shouldBe None
  }

  "removeAccents()" should "handle the empty string" in {
    HBaseCrossrefScore.removeAccents("") shouldBe ""
  }

  it should "not change a string with unaccented characters" in {
    HBaseCrossrefScore.removeAccents("abc123") shouldBe "abc123"
  }

  it should "remove accents from Ls" in {
    HBaseCrossrefScore.removeAccents("E\u0141\u0142en") shouldBe "ELlen"
  }

  it should "remove accents from Es without changing case" in {
    val result = HBaseCrossrefScore.removeAccents("\u00e9")
    result should have length 1
    result shouldBe "e"
  }

  it should "convert the ø in Soren" in {
    HBaseCrossrefScore.removeAccents("Søren") shouldBe "Soren"
    HBaseCrossrefScore.removeAccents("SØREN") shouldBe "SOREN"
  }

  // Tests adapted from https://oldfashionedsoftware.com/2009/11/19/string-distance-and-refactoring-in-scala/
  "stringDistance" should "work on empty strings" in {
    HBaseCrossrefScore.stringDistance("", "") shouldBe 0
    HBaseCrossrefScore.stringDistance("a", "") shouldBe 1
    HBaseCrossrefScore.stringDistance("", "a") shouldBe 1
    HBaseCrossrefScore.stringDistance("abc", "") shouldBe 3
    HBaseCrossrefScore.stringDistance("", "abc") shouldBe 3
  }

  it should "work on equal strings" in {
    HBaseCrossrefScore.stringDistance("", "") shouldBe 0
    HBaseCrossrefScore.stringDistance("a", "a") shouldBe 0
    HBaseCrossrefScore.stringDistance("abc", "abc") shouldBe 0
  }

  it should "work where only inserts are needed" in {
    HBaseCrossrefScore.stringDistance("", "a") shouldBe 1
    HBaseCrossrefScore.stringDistance("a", "ab") shouldBe 1
    HBaseCrossrefScore.stringDistance("b", "ab") shouldBe 1
    HBaseCrossrefScore.stringDistance("ac", "abc") shouldBe 1
    HBaseCrossrefScore.stringDistance("abcdefg", "xabxcdxxefxgx") shouldBe 6
  }

  it should "work where only deletes are needed" in {
    HBaseCrossrefScore.stringDistance( "a", "") shouldBe 1
    HBaseCrossrefScore.stringDistance( "ab", "a") shouldBe 1
    HBaseCrossrefScore.stringDistance( "ab", "b") shouldBe 1
    HBaseCrossrefScore.stringDistance("abc", "ac") shouldBe 1
    HBaseCrossrefScore.stringDistance("xabxcdxxefxgx", "abcdefg") shouldBe 6
  }

  it should "work where only substitutions are needed" in {
    HBaseCrossrefScore.stringDistance(  "a",   "b") shouldBe 1
    HBaseCrossrefScore.stringDistance( "ab",  "ac") shouldBe 1
    HBaseCrossrefScore.stringDistance( "ac",  "bc") shouldBe 1
    HBaseCrossrefScore.stringDistance("abc", "axc") shouldBe 1
    HBaseCrossrefScore.stringDistance("xabxcdxxefxgx", "1ab2cd34ef5g6") shouldBe 6
  }

  it should "work where many operations are needed" in {
    HBaseCrossrefScore.stringDistance("example", "samples") shouldBe 3
    HBaseCrossrefScore.stringDistance("sturgeon", "urgently") shouldBe 6
    HBaseCrossrefScore.stringDistance("levenshtein", "frankenstein") shouldBe 6
    HBaseCrossrefScore.stringDistance("distance", "difference") shouldBe 5
    HBaseCrossrefScore.stringDistance("java was neat", "scala is great") shouldBe 7
  }

  //  Pipeline tests

  val output = "/tmp/testOutput"
  val input = "/tmp/testInput"
  val (testTable, testHost) = ("test-table", "dummy-host:2181")

  val grobidSampleData = List(
    List(Bytes.toBytes("sha1:K2DKSSVTXWPRMFDTWSTCQW3RVWRIOV3Q"),
      Bytes.toBytes(GrobidString.replace("<<TITLE>>", "Title 1"))),
    List(Bytes.toBytes("sha1:C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ3WU"),
      Bytes.toBytes(GrobidString.replace("<<TITLE>>", "Title 2: TNG"))),
    List(Bytes.toBytes("sha1:SDKUVHC3YNNEGH5WAG5ZAAXWAEBNX4WT"),
      Bytes.toBytes(GrobidString.replace("<<TITLE>>", "Title 3: The Sequel"))),
    List(Bytes.toBytes("sha1:35985C3YNNEGH5WAG5ZAAXWAEBNXJW56"), 
      Bytes.toBytes(MalformedGrobidString)))

  JobTest("sandcrawler.HBaseCrossrefScoreJob")
    .arg("test", "")
    .arg("app.conf.path", "app.conf")
    .arg("output", output)
    .arg("hbase-table", testTable)
    .arg("zookeeper-hosts", testHost)
    .arg("crossref-input", input)
    .arg("debug", "true")
    .source[Tuple](HBaseCrossrefScore.getHBaseSource(testTable, testHost),
      grobidSampleData.map(l => new Tuple(l.map(s => {new ImmutableBytesWritable(s)}):_*)))
    .source(TextLine(input), List(
      0 -> CrossrefString.replace("<<TITLE>>", "Title 1: TNG").replace("<<DOI>>", "DOI-0"),
      1 -> CrossrefString.replace("<<TITLE>>", "Title 1: TNG 2").replace("<<DOI>>", "DOI-0.5"),
      2 -> CrossrefString.replace("<<TITLE>>", "Title 1: TNG 3").replace("<<DOI>>", "DOI-0.75"),
      3 -> CrossrefString.replace("<<TITLE>>", "Title 2: Rebooted").replace("<<DOI>>", "DOI-1")))
    .sink[(Int, String, String, String, String)](TypedTsv[(Int,
    String, String, String, String)](output)) {
      // Grobid titles: 
      //   "Title 1", "Title 2: TNG", "Title 3: The Sequel"
      // crossref slugs: 
      //   "Title 1: TNG", "Title 1: TNG 2", "Title 1: TNG 3", "Title 2 Rebooted"
      // Join should have 3 "Title  1" slugs and 1 "Title 2" slug
      outputBuffer =>
      "The pipeline" should "return a 4-element list" in {
        outputBuffer should have length 4
      }

      /*
      it should "return the right first entry" in {
        val (slug, slug0, slug1, sha1, grobidJson, crossrefJson) = outputBuffer(0)
        slug shouldBe "title 1"
        slug shouldBe slug0
        slug shouldBe slug1
        sha1 shouldBe new String(grobidSampleData(0)(0), "UTF-8")
        grobidJson shouldBe new String(grobidSampleData(0)(1), "UTF-8")
      }
       */
    }
    .run
    .finish
}
