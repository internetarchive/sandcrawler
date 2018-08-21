package sandcrawler

import java.io.InputStream

import scala.io.Source

import org.scalatest._

// scalastyle:off null
class ScorableFeaturesTest extends FlatSpec with Matchers {

  // TODO: Remove this when we're convinced that our file-reading code
  // works. (I'm already convinced. --Ellen)
  "read slugs" should "work" in {
    val SlugBlacklist = Set( "abbreviations", "abstract", "acknowledgements",
      "article", "authorreply", "authorsreply", "bookreview", "bookreviews",
      "casereport", "commentary", "commentaryon", "commenton", "commentto",
      "contents", "correspondence", "dedication", "editorialadvisoryboard",
      "focus", "hypothesis", "inbrief", "introduction", "introductiontotheissue",
      "lettertotheeditor", "listofabbreviations", "note", "overview", "preface",
      "references", "results", "review", "reviewarticle", "summary", "title",
      "name")

    ScorableFeatures.SlugBlacklist.size shouldBe SlugBlacklist.size
    for (s <- ScorableFeatures.SlugBlacklist) SlugBlacklist should contain (s)
  }

  private def titleToSlug(s : String) : String = {
    ScorableFeatures.create(title = s).toSlug
  }

  "toMapFeatures()" should "work with gnarly inputs" in {
    ScorableFeatures.create(title = null).toMapFeatures
    ScorableFeatures.create(title = "something", doi = null, sha1 = null, year = 123).toMapFeatures
  }

  "mapToSlug()" should "extract the parts of titles before a colon" in {
    titleToSlug("HELLO:there") shouldBe "hellothere"
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
    titleToSlug("HELLO!:the:re") shouldBe "hellothere"
    titleToSlug("a:b:c") shouldBe "abc"
    titleToSlug(
      "If you're happy and you know it, clap your hands!") shouldBe "ifyourehappyandyouknowitclapyourhands"
    titleToSlug(":;\"\'") shouldBe Scorable.NoSlug
  }

  it should "filter stub titles" in {
    titleToSlug("abstract") shouldBe Scorable.NoSlug
    titleToSlug("title!") shouldBe Scorable.NoSlug
    titleToSlug("a real title which is not on blacklist") shouldBe "arealtitlewhichisnotonblacklist"
  }

  it should "strip special characters" in {
    titleToSlug(":;!',|\"\'`.#?!-@*/\\=+~%$^{}()[]<>-_") shouldBe Scorable.NoSlug
    // TODO: titleToSlug("©™₨№…") shouldBe Scorable.NoSlug
    // TODO: titleToSlug("πµΣσ") shouldBe Scorable.NoSlug
  }

  it should "remove whitespace" in {
    titleToSlug("foo bar : baz ::") shouldBe "foobarbaz"
    titleToSlug("\na\t:b:c") shouldBe "abc"
    titleToSlug("\n \t \r  ") shouldBe Scorable.NoSlug
  }
}
