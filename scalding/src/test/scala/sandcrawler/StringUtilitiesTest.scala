package sandcrawler

import org.scalatest._

class StringUtilitiesTest extends FlatSpec with Matchers {
  "removeAccents()" should "handle the empty string" in {
    StringUtilities.removeAccents("") shouldBe ""
  }

  it should "not change a string with unaccented characters" in {
    StringUtilities.removeAccents("abc123") shouldBe "abc123"
  }

  it should "remove accents from Ls" in {
    StringUtilities.removeAccents("E\u0141\u0142en") shouldBe "ELlen"
  }

  it should "remove accents from Es without changing case" in {
    val result = StringUtilities.removeAccents("\u00e9")
    result should have length 1
    result shouldBe "e"
  }

  it should "convert the ø in Soren" in {
    StringUtilities.removeAccents("Søren") shouldBe "Soren"
    StringUtilities.removeAccents("SØREN") shouldBe "SOREN"
  }

  // Tests adapted from https://oldfashionedsoftware.com/2009/11/19/string-distance-and-refactoring-in-scala/
  "stringDistance" should "work on empty strings" in {
    StringUtilities.stringDistance("", "") shouldBe 0
    StringUtilities.stringDistance("a", "") shouldBe 1
    StringUtilities.stringDistance("", "a") shouldBe 1
    StringUtilities.stringDistance("abc", "") shouldBe 3
    StringUtilities.stringDistance("", "abc") shouldBe 3
  }

  it should "work on equal strings" in {
    StringUtilities.stringDistance("", "") shouldBe 0
    StringUtilities.stringDistance("a", "a") shouldBe 0
    StringUtilities.stringDistance("abc", "abc") shouldBe 0
  }

  it should "work where only inserts are needed" in {
    StringUtilities.stringDistance("", "a") shouldBe 1
    StringUtilities.stringDistance("a", "ab") shouldBe 1
    StringUtilities.stringDistance("b", "ab") shouldBe 1
    StringUtilities.stringDistance("ac", "abc") shouldBe 1
    StringUtilities.stringDistance("abcdefg", "xabxcdxxefxgx") shouldBe 6
  }

  it should "work where only deletes are needed" in {
    StringUtilities.stringDistance( "a", "") shouldBe 1
    StringUtilities.stringDistance( "ab", "a") shouldBe 1
    StringUtilities.stringDistance( "ab", "b") shouldBe 1
    StringUtilities.stringDistance("abc", "ac") shouldBe 1
    StringUtilities.stringDistance("xabxcdxxefxgx", "abcdefg") shouldBe 6
  }

  it should "work where only substitutions are needed" in {
    StringUtilities.stringDistance(  "a",   "b") shouldBe 1
    StringUtilities.stringDistance( "ab",  "ac") shouldBe 1
    StringUtilities.stringDistance( "ac",  "bc") shouldBe 1
    StringUtilities.stringDistance("abc", "axc") shouldBe 1
    StringUtilities.stringDistance("xabxcdxxefxgx", "1ab2cd34ef5g6") shouldBe 6
  }

  it should "work where many operations are needed" in {
    StringUtilities.stringDistance("example", "samples") shouldBe 3
    StringUtilities.stringDistance("sturgeon", "urgently") shouldBe 6
    StringUtilities.stringDistance("levenshtein", "frankenstein") shouldBe 6
    StringUtilities.stringDistance("distance", "difference") shouldBe 5
    StringUtilities.stringDistance("java was neat", "scala is great") shouldBe 7
  }
}
