package sandcrawler

import java.io.InputStream

import scala.io.Source
import scala.util.parsing.json.JSONArray
import scala.util.parsing.json.JSONObject

object ScorableFeatures {
  // TODO: Add exception handling.
  val fileStream : InputStream = getClass.getResourceAsStream("/slug-denylist.txt")
  val SlugDenylist : Set[String] = Source.fromInputStream(fileStream).getLines.toSet
  fileStream.close
  val MinSlugLength = 8

  // Static factory method
  def create(title : String, authors : List[Any] = List(), year : Int = 0, doi : String = "", sha1 : String = "") : ScorableFeatures = {
    new ScorableFeatures(
      title=if (title == null) "" else title,
      authors=if (authors == null) List() else authors.map(a => if (a == null) "" else a),
      year=year,
      doi=if (doi == null) "" else doi,
      sha1=if (sha1 == null) "" else sha1)
  }
}

// Contains features needed to make slug and to score (in combination
// with a second ScorableFeatures). Create with above static factory method.
class ScorableFeatures private(title : String, authors : List[Any] = List(), year: Int = 0, doi : String = "", sha1: String = "") {

  def toMap() : Map[String, Any] =
    Map("title" -> title, "authors" -> JSONArray(authors), "year" -> year, "doi" -> doi, "sha1" -> sha1)

  override def toString() : String = {
    JSONObject(toMap).toString
  }

  def toSlug() : Option[String] = {
    if (title == null) {
      None
    } else {
      val unaccented = StringUtilities.removeAccents(title)
      // Remove punctuation
      val slug = StringUtilities.removePunctuation((unaccented.toLowerCase())).replaceAll("\\s", "")
      if (slug.isEmpty
        || slug == null
        || (ScorableFeatures.SlugDenylist contains slug)
        || (slug.length < ScorableFeatures.MinSlugLength)) {
        None
      } else {
        Some(slug)
      }
    }
  }

  def toMapFeatures : Option[MapFeatures] =
    toSlug match {
      case None => None
      case Some(slug) => Some(MapFeatures(slug, toString))
    }
}
