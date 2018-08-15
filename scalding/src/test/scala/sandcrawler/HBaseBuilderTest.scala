package sandcrawler

import cascading.tuple.Fields
import org.scalatest._

class HBaseBuilderTest extends FlatSpec with Matchers {
  "parseColSpecs()" should "work on legal nontrivial input" in {
    val (fams, fields) = HBaseBuilder.parseColSpecs(List("file:size", "file:cdx", "match0:status"))
    fams should have length 2
    fields should have length 2
    val fileIndex = fams.indexOf("file")
    fileIndex should not be -1
    fields(fileIndex) should be (new Fields("size", "cdx"))
    val match0Index = fams.indexOf("match0")
    match0Index should not be -1
    fields(match0Index) should be (new Fields("status"))
  }

  it should "work on empty input" in {
    val (fams, fields) = HBaseBuilder.parseColSpecs(List())
    fams should have length 0
    fields should have length 0
  }

  //scalastyle:off no.whitespace.before.left.bracket
  it should "throw IllegalArgumentException on malformed input" in {
    a [IllegalArgumentException] should be thrownBy {
      HBaseBuilder.parseColSpecs(List("file_size"))
    }
  }

  it should "throw IllegalArgumentException on nonexistent family" in {
    a [IllegalArgumentException] should be thrownBy {
      HBaseBuilder.parseColSpecs(List("foo:bar"))
    }
  }

  it should "throw IllegalArgumentException on nonexistent column" in {
    a [IllegalArgumentException] should be thrownBy {
      HBaseBuilder.parseColSpecs(List("file:bar"))
    }
  }
}
