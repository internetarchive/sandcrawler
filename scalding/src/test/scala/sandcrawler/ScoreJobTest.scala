package sandcrawler

import cascading.tuple.Fields
import cascading.tuple.Tuple
import com.twitter.scalding.{JobTest, TextLine, TypedTsv, TupleConversions}
import org.apache.hadoop.hbase.io.ImmutableBytesWritable
import org.apache.hadoop.hbase.util.Bytes
import org.scalatest._
import parallelai.spyglass.hbase.HBaseConstants.SourceMode

class ScoreJobTest extends FlatSpec with Matchers {
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
  val JsonStringWithTitle = JsonString.replace("<<TITLE>>", "Dummy Example File")
  val JsonStringWithoutTitle = JsonString.replace("title", "nottitle")
  val MalformedJsonString = JsonString.replace("}", "")

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
  val CrossrefStrings = List(
    CrossrefString.replace("<<TITLE>>", "Title 1: TNG").replace("<<DOI>>", "DOI-0"),
    CrossrefString.replace("<<TITLE>>", "Title 1: TNG 2A").replace("<<DOI>>", "DOI-0.5"),
    CrossrefString.replace("<<TITLE>>", "Title 1: TNG 3").replace("<<DOI>>", "DOI-0.75"),
    CrossrefString.replace("<<TITLE>>", "Title 2: Rebooted").replace("<<DOI>>", "DOI-1"))

  //  Pipeline tests
  val output = "/tmp/testOutput"
  val input = "/tmp/testInput"
  val (testTable, testHost) = ("test-table", "dummy-host:2181")

  val Sha1Strings : List[String] = List(
    "sha1:K2DKSSVTXWPRMFDTWSTCQW3RVWRIOV3Q",
    "sha1:C3YNNEGH5WAG5ZAAXWAEBNXJWT6CZ3WU",
    "sha1:SDKUVHC3YNNEGH5WAG5ZAAXWAEBNX4WT",
    "sha1:35985C3YNNEGH5WAG5ZAAXWAEBNXJW56",
    "sha1:93187A85273589347598473894839443",
    "sha1:024937534094897039547e9824382943")

  val JsonStrings : List[String] = List(
    JsonString.replace("<<TITLE>>", "Title 1"),
    JsonString.replace("<<TITLE>>", "Title 2: TNG"),
    JsonString.replace("<<TITLE>>", "Title 3: The Sequel"),
    // This will have bad status.
    JsonString.replace("<<TITLE>>", "Title 1"),
    MalformedJsonString,
    // This will have bad status.
    JsonString.replace("<<TITLE>>", "Title 2")
  )

  val Ok = "200"
  val Bad = "400"
  val StatusCodes = List(Ok, Ok, Ok, Bad, Ok, Bad)

  val SampleData : List[List[Array[Byte]]] = (Sha1Strings, JsonStrings, StatusCodes)
    .zipped
    .toList
    .map { case (sha, json, status) => List(Bytes.toBytes(sha), Bytes.toBytes(json), Bytes.toBytes(status)) }

  JobTest("sandcrawler.ScoreJob")
    .arg("test", "")
    .arg("app.conf.path", "app.conf")
    .arg("output", output)
    .arg("hbase-table", testTable)
    .arg("zookeeper-hosts", testHost)
    .arg("crossref-input", input)
    .arg("debug", "true")
    .source[Tuple](GrobidScorable.getHBaseSource(testTable, testHost),
      SampleData.map(l => new Tuple(l.map(s => {new ImmutableBytesWritable(s)}):_*)))
    .source(TextLine(input), List(
      0 -> CrossrefStrings(0),
      1 -> CrossrefStrings(1),
      2 -> CrossrefStrings(2),
      3 -> CrossrefStrings(3)))
    .sink[(String, Int, String, String)](TypedTsv[(String, Int, String, String)](output)) {
      // Grobid titles and slugs (in parentheses): 
      //   Title 1                       (title1)
      //   Title 2: TNG                  (title2)
      //   Title 3: The Sequel           (title3)
      // crossref titles and slugs (in parentheses):
      //   Title 1: TNG                  (title1)
      //   Title 1: TNG 2A               (title1)
      //   Title 1: TNG 3                (title1)
      //   Title 2: Rebooted             (title2)
      // Join should have 3 "title1" slugs and 1 "title2" slug
      outputBuffer => 
      "The pipeline" should "return a 4-element list" in {
        outputBuffer should have length 4
      }

      it should "has right # of entries with each slug" in {
        val slugs = outputBuffer.map(_._1)
        val countMap : Map[String, Int] = slugs.groupBy(identity).mapValues(_.size)
        countMap("title1") shouldBe 3
        countMap("title2") shouldBe 1
      }

      def bundle(slug : String, grobidIndex : Int, crossrefIndex : Int) = {
        val mf1 : MapFeatures = GrobidScorable.jsonToMapFeatures(
          Sha1Strings(grobidIndex), 
          JsonStrings(grobidIndex))
        val mf2 : MapFeatures = CrossrefScorable.jsonToMapFeatures(
          CrossrefStrings(crossrefIndex))
        val score = Scorable.computeSimilarity(
          ReduceFeatures(mf1.json),
          ReduceFeatures(mf2.json))
        (slug, score, mf1.json, mf2.json)
      }

      it should "have right output values" in {
        outputBuffer.exists(_ == bundle("title1", 0, 0))
        outputBuffer.exists(_ == bundle("title1", 0, 2))
        outputBuffer.exists(_ == bundle("title1", 0, 1))
        outputBuffer.exists(_ == bundle("title2", 1, 3))
      }
    }
    .run
    .finish
}
