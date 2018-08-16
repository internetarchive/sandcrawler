package sandcrawler

import scala.util.parsing.json.JSONObject

// Contains features needed to make slug and to score (in combination
// with a second ScorableFeatures).
class ScorableFeatures(title : String, year: Int = 0, doi : String = "", sha1: String = "") {
  def toMap() : Map[String, Any] = {
    Map("title" -> (if (title == null) "" else title),
        "year" -> year,
        "doi" -> (if (doi == null) "" else doi),
        "sha1" -> (if (sha1 == null) "" else sha1))
  }

  override def toString() : String = {
    JSONObject(toMap()).toString
  }

  def toSlug() : String = {
    if (title == null) {
      Scorable.NoSlug
    } else {
      val unaccented = StringUtilities.removeAccents(title)
      // Remove punctuation after splitting on colon.
      val slug = StringUtilities.removePunctuation((unaccented.split(":")(0).toLowerCase())).replaceAll("\\s", "")
      if (slug.isEmpty || slug == null) Scorable.NoSlug else slug
    }
  }

  def toMapFeatures = {
    MapFeatures(toSlug, toString)
  }
}
