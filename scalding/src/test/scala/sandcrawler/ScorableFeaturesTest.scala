package sandcrawler

import java.io.InputStream

import scala.io.Source

import org.scalatest._

// scalastyle:off null
class ScorableFeaturesTest extends FlatSpec with Matchers {
  "toMapFeatures()" should "work with gnarly inputs" in {
    ScorableFeatures.create(title = null).toMapFeatures
    ScorableFeatures.create(title = "something", doi = null, sha1 = null, year = 123).toMapFeatures
  }

  private def titleToSlug(s : String) : Option[String] = ScorableFeatures.create(title = s).toSlug

  "mapToSlug()" should "extract the parts of titles before a colon" in {
    titleToSlug("HELLO:there") shouldBe Some("hellothere")
  }

  it should "extract an entire colon-less string" in {
    titleToSlug("hello THERE") shouldBe Some("hellothere")
  }

  it should "return Scorable.NoSlug if given empty string" in {
    titleToSlug("") shouldBe (None)
  }

  it should "return Scorable.NoSlug if given null" in {
    titleToSlug(null) shouldBe (None)
  }

  it should "strip punctuation" in {
    titleToSlug("HELLO!:the:re") shouldBe Some("hellothere")
    titleToSlug("a:b:cdefgh") shouldBe Some("abcdefgh")
    titleToSlug(
      "If you're happy and you know it, clap your hands!") shouldBe Some("ifyourehappyandyouknowitclapyourhands")
    titleToSlug(":;\"\'") shouldBe (None)
  }

  it should "filter stub titles" in {
    titleToSlug("abstract") shouldBe (None)
    titleToSlug("title!") shouldBe (None)
    titleToSlug("a real title which is not on denylist") shouldBe Some("arealtitlewhichisnotondenylist")
  }

  it should "strip special characters" in {
    titleToSlug(":;!',|\"\'`.#?!-@*/\\=+~%$^{}()[]<>-_’·“”‘’“”«»「」¿–±§ʿ") shouldBe (None)
    // TODO: titleToSlug("©™₨№…") shouldBe (None)
    // TODO: titleToSlug("πµΣσ") shouldBe (None)
  }

  it should "remove whitespace" in {
    titleToSlug("foo bar : baz ::") shouldBe Some("foobarbaz")
    titleToSlug("\na\t:b:cdefghi") shouldBe Some("abcdefghi")
    titleToSlug("\n \t \r  ") shouldBe (None)
  }

  it should "skip very short slugs" in {
    titleToSlug("short") shouldBe (None)
    titleToSlug("a longer, more in depth title") shouldBe Some("alongermoreindepthtitle")
  }
}
