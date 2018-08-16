package sandcrawler

import org.scalatest._

// scalastyle:off null
class ScorableFeaturesTest extends FlatSpec with Matchers {
  private def titleToSlug(s : String) : String = {
    new ScorableFeatures(title = s).toSlug
  }

  "toMapFeatures()" should "work with gnarly inputs" in {
    new ScorableFeatures(title = null).toMapFeatures
    new ScorableFeatures(title = "something", doi = null, sha1 = null, year = 123).toMapFeatures
  }

  "mapToSlug()" should "extract the parts of titles before a colon" in {
    titleToSlug("HELLO:there") shouldBe "hello"
  }

  it should "extract an entire colon-less string" in {
    titleToSlug("hello THERE") shouldBe "hellothere"
  }

  it should "return Scorable.NoSlug if given empty string" in {
    titleToSlug("") shouldBe Scorable.NoSlug
  }

  it should "return Scorable.NoSlug if given null" in {
    titleToSlug(null) shouldBe Scorable.NoSlug
  }

  it should "strip punctuation" in {
    titleToSlug("HELLO!:the:re") shouldBe "hello"
    titleToSlug("a:b:c") shouldBe "a"
    titleToSlug(
      "If you're happy and you know it, clap your hands!") shouldBe "ifyourehappyandyouknowitclapyourhands"
  }

  it should "remove whitespace" in {
    titleToSlug("foo bar : baz ::") shouldBe "foobar"
    titleToSlug("\na\t:b:c") shouldBe "a"
  }
}
